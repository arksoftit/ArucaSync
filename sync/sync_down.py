import pyodbc
import pg8000.dbapi
from sync_logger import LogManager
from arucasyncdb import ArucaSyncDBManager


class SyncDown:
    def __init__(self, manager_local, config_remota):
        self.manager_local = manager_local
        self.config_remota = config_remota

    def _conectar_remoto(self):
        return pg8000.dbapi.connect(
            host=self.config_remota["server"],
            port=int(self.config_remota["port"]),
            database=self.config_remota["database"],
            user=self.config_remota["username"],
            password=self.config_remota["password"],
            ssl_context=None
        )

    def obtener_clientes_pendientes(self):
        remoto = self._conectar_remoto()
        cursor_remoto = remoto.cursor()
        cursor_remoto.execute("""
            SELECT cli_codigo, cli_descripcion, cli_status, cli_clasificacion, 
                   cli_descripciondetallada, cli_nit, cli_rif, cli_contacto, 
                   cli_direccion1, cli_direccion2, cli_direccion3, cli_telefono, 
                   cli_telefax, cli_email, cli_zona, cli_vendedor, cli_cobrador, cli_moneda,
                   cli_systemdate
            FROM public.arc_clientes WHERE cli_sync_status = false
        """)
        clientes = cursor_remoto.fetchall()
        cursor_remoto.close()
        remoto.close()
        return clientes

    def bajar_clientes(self):
        self.logger = LogManager()
        self.logger.info("Iniciando sincronización de bajada para Clientes...")

        clientes = self.obtener_clientes_pendientes()

        if not clientes:
            self.logger.cerrar("No hay clientes pendientes por bajar.")
            return 0

        ok, msg, conn_local = self.manager_local.open_connection()
        if not ok:
            self.logger.error(f"Error conexión DBISAM: {msg}")
            return 0

        conn_local.setdecoding(pyodbc.SQL_CHAR, encoding='latin-1')
        conn_local.setencoding(encoding='latin-1')

        cursor_local = conn_local.cursor()
        contador = 0

        try:
            for fila in clientes:
                fecha_inicio = None
                if fila[18] is not None:
                    fecha_inicio = fila[18].strftime('%Y-%m-%d')

                datos_insert = tuple(fila[:18]) + (True, fecha_inicio)

                cursor_local.execute("""
                    INSERT INTO Sclientes (
                        FC_CODIGO, FC_DESCRIPCION, FC_STATUS, FC_CLASIFICACION, FC_DESCRIPCIONDETALLADA, 
                        FC_NIT, FC_RIF, FC_CONTACTO, FC_DIRECCION1, FC_DIRECCION2, FC_DIRECCION3, 
                        FC_TELEFONO, FC_TELEFAX, FC_EMAIL, FC_ZONA, FC_VENDEDOR, FC_COBRADOR, FC_MONEDA,
                        FC_RECORDCONTADO, FC_FECHAINICIO
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, datos_insert)
                
                cursor_local.close()
                cursor_fixed = conn_local.cursor()
                cursor_fixed.execute("""
                    INSERT INTO SFixed (FX_TIPO, FX_CODIGO, FX_VISIBLE) VALUES (?, ?, ?)
                """, ('9', fila[0], True))
                cursor_fixed.close()
                cursor_local = conn_local.cursor()
                
                contador += 1

            conn_local.commit()
            
            codigos_bajados = tuple(str(c[0]) for c in clientes)
            placeholders = ','.join(['%s'] * len(codigos_bajados))
            cursor_remoto = self._conectar_remoto().cursor()
            cursor_remoto.execute(
                f"UPDATE public.arc_clientes SET cli_sync_status = true WHERE cli_codigo IN ({placeholders})", 
                codigos_bajados
            )
            cursor_remoto.connection.commit()
            cursor_remoto.close()
            
            self.logger.cerrar(f"Sincronización de bajada completada. Clientes insertados: {contador}.")
            return contador
            
        except Exception as e:
            conn_local.rollback()
            self.logger.error(f"Error en sincronización de bajada: {str(e)}")
            raise e
        finally:
            cursor_local.close()
            conn_local.close()

    def obtener_transacciones_pendientes(self):
        remoto = self._conectar_remoto()
        cursor_remoto = remoto.cursor()
        cursor_remoto.execute("""
            SELECT trn_tipo, trn_personacontacto, trn_documento, trn_totalitems, trn_totalbruto, 
                   trn_baseimponible, trn_impuesto1monto, trn_totalneto, trn_sync_status
            FROM public.arc_transacciones 
            WHERE trn_sync_status = false
            ORDER BY trn_tipo, trn_documento
        """)
        transacciones = cursor_remoto.fetchall()
        cursor_remoto.close()
        remoto.close()
        return transacciones

    def bajar_transacciones(self, fecha_desde="", fecha_hasta=""):
        self.logger = LogManager()
        self.logger.info("Iniciando sincronización de bajada para Transacciones (Cabeceras y Detalles)...")
        
        db_local = ArucaSyncDBManager()

        remoto = self._conectar_remoto()
        cursor_remoto = remoto.cursor()

        columnas_mapa = [
            ("trn_tipo", "FTI_TIPO"),
            ("trn_documento", "FTI_DOCUMENTO"),
            ("trn_status", "FTI_STATUS"),
            ("trn_visible", "FTI_VISIBLE"),
            ("trn_fechaemision", "FTI_FECHAEMISION"),
            ("trn_depositosource", "FTI_DEPOSITOSOURCE"),
            ("trn_depositodestino", "FTI_DEPOSITODESTINO"),
            ("trn_totalitems", "FTI_TOTALITEMS"),
            ("trn_totalitemsinicial", "FTI_TOTALITEMSINICIAL"),
            ("trn_moneda", "FTI_MONEDA"),
            ("trn_factorcambio", "FTI_FACTORCAMBIO"),
            ("trn_totalcosto", "FTI_TOTALCOSTO"),
            ("trn_totalcostoreal", "FTI_TOTALCOSTOREAL"),
            ("trn_clasificacion", "FTI_CLASIFICACION"),
            ("trn_descripclasify", "FTI_DESCRIPCLASIFY"),
            ("trn_user", "FTI_USER"),
            ("trn_autorizadopor", "FTI_AUTORIZADOPOR"),
            ("trn_proposito", "FTI_PROPOSITO"),
            ("trn_responsable", "FTI_RESPONSABLE"),
            ("trn_detalle", "FTI_DETALLE"),
            ("trn_tienelotes", "FTI_TIENELOTES"),
            ("trn_updateitems", "FTI_UPDATEITEMS"),
            ("trn_totalbruto", "FTI_TOTALBRUTO"),
            ("trn_descuento1porcent", "FTI_DESCUENTO1PORCENT"),
            ("trn_descuento1monto", "FTI_DESCUENTO1MONTO"),
            ("trn_descuento1origen", "FTI_DESCUENTO1ORIGEN"),
            ("trn_descuento2porcent", "FTI_DESCUENTO2PORCENT"),
            ("trn_descuento2monto", "FTI_DESCUENTO2MONTO"),
            ("trn_descuento2origen", "FTI_DESCUENTO2ORIGEN"),
            ("trn_descuentoparcial", "FTI_DESCUENTOPARCIAL"),
            ("trn_fleteporcent", "FTI_FLETEPORCENT"),
            ("trn_fletemoneda", "FTI_FLETEMONEDA"),
            ("trn_fleteorigen", "FTI_FLETEORIGEN"),
            ("trn_baseimponible", "FTI_BASEIMPONIBLE"),
            ("trn_baseimponible2", "FTI_BASEIMPONIBLE2"),
            ("trn_impuesto1porcent", "FTI_IMPUESTO1PORCENT"),
            ("trn_impuesto1monto", "FTI_IMPUESTO1MONTO"),
            ("trn_impuesto2porcent", "FTI_IMPUESTO2PORCENT"),
            ("trn_impuesto2monto", "FTI_IMPUESTO2MONTO"),
            ("trn_descuentocuadre", "FTI_DESCUENTOCUADRE"),
            ("trn_totalneto", "FTI_TOTALNETO"),
            ("trn_fechavencido", "FTI_FECHAVENCIDO"),
            ("trn_diasvencimiento", "FTI_DIASVENCIMIENTO"),
            ("trn_rifcliente", "FTI_RIFCLIENTE"),
            ("trn_nitcliente", "FTI_NITCLIENTE"),
            ("trn_personacontacto", "FTI_PERSONACONTACTO"),
            ("trn_telefonocontacto", "FTI_TELEFONOCONTACTO"),
            ("trn_direcciondespacho", "FTI_DIRECCIONDESPACHO"),
            ("trn_detallecomentario", "FTI_DETALLECOMENTARIO"),
            ("trn_ordencompra", "FTI_ORDENCOMPRA"),
            ("trn_existeplanillaimportacion", "FTI_EXISTEPLANILLAIMPORTACION"),
            ("trn_porcentfletesinasignar", "FTI_PORCENTFLETESINASIGNAR"),
            ("trn_saldooperacion", "FTI_SALDOOPERACION"),
            ("trn_monedapago", "FTI_MONEDAPAGO"),
            ("trn_totalprecio", "FTI_TOTALPRECIO"),
            ("trn_vuelto", "FTI_VUELTO"),
            ("trn_autorizados", "FTI_AUTORIZADOS"),
            ("trn_excento", "FTI_EXCENTO"),
            ("trn_costodeventa", "FTI_COSTODEVENTA"),
            ("trn_tipooperacionorigen", "FTI_TIPOOPERACIONORIGEN"),
            ("trn_documentoorigen", "FTI_DOCUMENTOORIGEN"),
            ("trn_fromcompuestos", "FTI_FROMCOMPUESTOS"),
            ("trn_vendedorasignado", "FTI_VENDEDORASIGNADO"),
            ("trn_zonaventa", "FTI_ZONAVENTA"),
            ("trn_pendingforprint", "FTI_PENDINGFORPRINT"),
            ("trn_cobradorasignado", "FTI_COBRADORASIGNADO"),
            ("trn_comisioncobros", "FTI_COMISIONCOBROS"),
            ("trn_comisioncobrosbloqueada", "FTI_COMISIONCOBROSBLOQUEADA"),
            ("trn_facturasloterandom", "FTI_FACTURASLOTERANDOM"),
            ("trn_multiplevendedor", "FTI_MULTIPLEVENDEDOR"),
            ("trn_multipledeposito", "FTI_MULTIPLEDEPOSITO"),
            ("trn_timesaved", "FTI_TIMESAVED"),
            ("trn_tipoprecio", "FTI_TIPOPRECIO"),
            ("trn_serie", "FTI_SERIE"),
            ("trn_nameformato", "FTI_NAMEFORMATO"),
            ("trn_machinename", "FTI_MACHINENAME"),
            ("trn_comisionventa", "FTI_COMISIONVENTA"),
            ("trn_montopagado", "FTI_MONTOPAGADO"),
            ("trn_montoperiodo", "FTI_MONTOPERIODO"),
            ("trn_porcentperiodo", "FTI_PORCENTPERIODO"),
            ("trn_hora", "FTI_HORA"),
            ("trn_guiadespacho", "FTI_GUIADESPACHO"),
            ("trn_norecibocaja", "FTI_NORECIBOCAJA"),
            ("trn_ctocosto", "FTI_CTOCOSTO"),
            ("trn_costoactualnacional", "FTI_COSTOACTUALNACIONAL"),
            ("trn_costoactualex", "FTI_COSTOACTUALEX"),
            ("trn_prefixinventario", "FTI_PREFIXINVENTARIO"),
            ("trn_numerocontrol", "FTI_NUMEROCONTROL"),
            ("trn_costoajustado", "FTI_COSTOAJUSTADO"),
            ("trn_factorreferencia", "FTI_FACTORREFERENCIA"),
            ("trn_finicial", "FTI_FINICIAL"),
            ("trn_fintereses", "FTI_FINTERESES"),
            ("trn_finteresesp", "FTI_FINTERESESP"),
            ("trn_fmanejo", "FTI_FMANEJO"),
            ("trn_fmanejop", "FTI_FMANEJOP"),
            ("trn_fextraordinaria", "FTI_FEXTRAORDINARIA"),
            ("trn_fctdextraordinaria", "FTI_FCTDEXTRAORDINARIA"),
            ("trn_fintextraordinaria", "FTI_FINTEXTRAORDINARIA"),
            ("trn_fmtocuota", "FTI_FMTOCUOTA"),
            ("trn_fctdcuota", "FTI_FCTDCUOTA"),
            ("trn_fcobranza", "FTI_FCOBRANZA"),
            ("trn_totalfinanciado", "FTI_TOTALFINANCIADO"),
            ("trn_saldofinanciar", "FTI_SALDOFINANCIAR"),
            ("trn_primeracuota", "FTI_PRIMERACUOTA"),
            ("trn_capitalcuotaextra", "FTI_CAPITALCUOTAEXTRA"),
            ("trn_credicard", "FTI_CREDICARD"),
            ("trn_maquinafiscal", "FTI_MAQUINAFISCAL"),
            ("trn_totalpaginas", "FTI_TOTALPAGINAS"),
            ("trn_sucursalorigen", "FTI_SUCURSALORIGEN"),
            ("trn_fechalibro", "FTI_FECHALIBRO"),
            ("trn_ivaintereses", "FTI_IVAINTERESES"),
            ("trn_reimpresafiscal", "FTI_REIMPRESAFISCAL"),
            ("trn_dctofiscalorigen", "FTI_DCTOFISCALORIGEN"),
            ("trn_fechafactura", "FTI_FECHAFACTURA"),
            ("trn_dctoiva", "FTI_DCTOIVA"),
            ("trn_monedacambio", "FTI_MONEDACAMBIO"),
            ("trn_tipofactorcambio", "FTI_TIPOFACTORCAMBIO"),
            ("trn_origencambio", "FTI_ORIGENCAMBIO"),
            ("trn_factorvuelto", "FTI_FACTORVUELTO"),
            ("trn_codecambio", "FTI_CODECAMBIO"),
            ("trn_vueltoorg", "FTI_VUELTOORG"),
            ("trn_vtanapago", "FTI_VTANAPAGO"),
            ("trn_factorreferencia2", "FTI_FACTORREFERENCIA2"),
            ("trn_multivuelto", "FTI_MULTIVUELTO"),
            ("trn_extrafield01", "FTI_EXTRAFIELD01"),
            ("trn_extrafield02", "FTI_EXTRAFIELD02"),
            ("trn_extrafield03", "FTI_EXTRAFIELD03"),
            ("trn_extrafield04", "FTI_EXTRAFIELD04"),
            ("trn_extrafield05", "FTI_EXTRAFIELD05"),
            ("trn_baseigtf", "FTI_BASEIGTF"),
            ("trn_extrafield06", "FTI_EXTRAFIELD06"),
            ("trn_imprentaasignacion", "FTI_IMPRENTAASIGNACION"),
            ("trn_imprentahora", "FTI_IMPRENTAHORA"),
            ("trn_statusimprenta", "FTI_STATUSIMPRENTA"),
            ("trn_imprentadocorigen", "FTI_IMPRENTADOCORIGEN"),
            ("trn_imprentamotivo", "FTI_IMPRENTAMOTIVO"),
            ("trn_imprentafechaorigen", "FTI_IMPRENTAFECHAORIGEN"),
            ("trn_imprentaserieorigen", "FTI_IMPRENTASERIEORIGEN"),
            ("trn_imprentamtoorigen", "FTI_IMPRENTAMTOORIGEN"),
            ("trn_mtootroscargos", "FTI_MTOOTROSCARGOS")
        ]

        columnas_mapa_det = [
            ("dtv_tipooperacion", "FDI_TIPOOPERACION"),
            ("dtv_documento", "FDI_DOCUMENTO"),
            ("dtv_linea", "FDI_LINEA"),
            ("dtv_codigo", "FDI_CODIGO"),
            ("dtv_status", "FDI_STATUS"),
            ("dtv_visible", "FDI_VISIBLE"),
            ("dtv_costo", "FDI_COSTO"),
            ("dtv_cantidad", "FDI_CANTIDAD"),
            ("dtv_cantidadpendiente", "FDI_CANTIDADPENDIENTE"),
            ("dtv_depositosource", "FDI_DEPOSITOSOURCE"),
            ("dtv_decimales", "FDI_DECIMALES"),
            ("dtv_decimalespen", "FDI_DECIMALESPEN"),
            ("dtv_serialnumber", "FDI_SERIALNUMBER"),
            ("dtv_usaseriales", "FDI_USASERIALES"),
            ("dtv_usadepositos", "FDI_USADEPOSITOS"),
            ("dtv_costooperacion", "FDI_COSTOOPERACION"),
            ("dtv_moneda", "FDI_MONEDA"),
            ("dtv_factorcambio", "FDI_FACTORCAMBIO"),
            ("dtv_existedetalleimportacion", "FDI_EXISTEDETALLEIMPORTACION"),
            ("dtv_existedetalledecostos", "FDI_EXISTEDETALLEDECOSTOS"),
            ("dtv_alicuotafleteotros", "FDI_ALICUOTAFLETEOTROS"),
            ("dtv_impuesto1", "FDI_IMPUESTO1"),
            ("dtv_porcentimpuesto1", "FDI_PORCENTIMPUESTO1"),
            ("dtv_montoimpuesto1", "FDI_MONTOIMPUESTO1"),
            ("dtv_impuesto2", "FDI_IMPUESTO2"),
            ("dtv_porcentimpuesto2", "FDI_PORCENTIMPUESTO2"),
            ("dtv_montoimpuesto2", "FDI_MONTOIMPUESTO2"),
            ("dtv_origenprice", "FDI_ORIGENPRICE"),
            ("dtv_porcentdescparcial", "FDI_PORCENTDESCPARCIAL"),
            ("dtv_descuentoparcial", "FDI_DESCUENTOPARCIAL"),
            ("dtv_preciosindescuento", "FDI_PRECIOSINDESCUENTO"),
            ("dtv_preciocondescuento", "FDI_PRECIOCONDESCUENTO"),
            ("dtv_preciodeventa", "FDI_PRECIODEVENTA"),
            ("dtv_rounddesctparcial", "FDI_ROUNDDESCTPARCIAL"),
            ("dtv_comisionfija", "FDI_COMISIONFIJA"),
            ("dtv_comisionfijap", "FDI_COMISIONFIJAP"),
            ("dtv_unddescarga", "FDI_UNDDESCARGA"),
            ("dtv_undcapacidad", "FDI_UNDCAPACIDAD"),
            ("dtv_unddetallada", "FDI_UNDDETALLADA"),
            ("dtv_indexprices", "FDI_INDEXPRICES"),
            ("dtv_partesusanseriales", "FDI_PARTESUSANSERIALES"),
            ("dtv_costodeventas", "FDI_COSTODEVENTAS"),
            ("dtv_vendedorasignado", "FDI_VENDEDORASIGNADO"),
            ("dtv_montocomision", "FDI_MONTOCOMISION"),
            ("dtv_preciobasecomision", "FDI_PRECIOBASECOMISION"),
            ("dtv_comisionbloqueada", "FDI_COMISIONBLOQUEADA"),
            ("dtv_comisionyapagada", "FDI_COMISIONYAPAGADA"),
            ("dtv_tipodecomision", "FDI_TIPODECOMISION"),
            ("dtv_priceforcomision", "FDI_PRICEFORCOMISION"),
            ("dtv_fechaoperacion", "FDI_FECHAOPERACION"),
            ("dtv_user", "FDI_USER"),
            ("dtv_porcentdescuento1", "FDI_PORCENTDESCUENTO1"),
            ("dtv_porcentdescuento2", "FDI_PORCENTDESCPARCIAL"),
            ("dtv_costosupdate", "FDI_COSTOSUPDATE"),
            ("dtv_totalpeso", "FDI_TOTALPESO"),
            ("dtv_ctocosto", "FDI_CTOCOSTO"),
            ("dtv_costoactualnacional", "FDI_COSTOACTUALNACIONAL"),
            ("dtv_costoactualext", "FDI_COSTOACTUALEXT"),
            ("dtv_costoajustado", "FDI_COSTOAJUSTADO"),
            ("dtv_fechalibro", "FDI_FECHALIBRO"),
            ("dtv_montoliquidado", "FDI_MONTOLIQUIDADO"),
            ("dtv_tipodocumentoorigen", "FDI_TIPODOCUMENTOORIGEN"),
            ("dtv_statusdocumentoorigen", "FDI_STATUSDOCUMENTOORIGEN"),
            ("dtv_dctoiva", "FDI_DCTOIVA"),
            ("dtv_montoimpuesto1dcto", "FDI_MONTOIMPUESTO1DCTO"),
            ("dtv_preciodeventadcto", "FDI_PRECIODEVENTADCTO"),
            ("dtv_clienteproveedor", "FDI_CLIENTEPROVEEDOR")
        ]

        cols_pg = [p[0] for p in columnas_mapa]
        columnas_cab = [p[1] for p in columnas_mapa]

        query = f"SELECT {', '.join(cols_pg)} FROM public.arc_transacciones WHERE trn_sync_status = false"
        params = []
        if fecha_desde and fecha_hasta:
            query += " AND trn_fechaemision >= %s AND trn_fechaemision <= %s"
            params.extend([fecha_desde, fecha_hasta])
            
        cursor_remoto.execute(query, tuple(params))
        
        nombres_cols_remotas = [desc[0].lower() for desc in cursor_remoto.description]
        filas = cursor_remoto.fetchall()

        if not filas:
            self.logger.cerrar("No hay transacciones pendientes por bajar.")
            cursor_remoto.close()
            remoto.close()
            return 0

        ok, msg, conn_local = self.manager_local.open_connection()
        if not ok:
            self.logger.error(f"Error conexión DBISAM: {msg}")
            cursor_remoto.close()
            remoto.close()
            return 0

        conn_local.setdecoding(pyodbc.SQL_CHAR, encoding='latin-1')
        conn_local.setencoding(encoding='latin-1')
        cursor_local = conn_local.cursor()
        
        contador = 0

        def formatear_valor_sql(val):
            if val is None:
                return "NULL"
            if isinstance(val, bool):
                return "True" if val else "False"
            if isinstance(val, (int, float)):
                return str(val)
            if isinstance(val, str):
                if len(val) >= 10 and val[4:5] == '-' and val[7:8] == '-' and 'T' in val:
                    try:
                        val = val.split('T')[0]
                    except Exception:
                        pass
                val_clean = val.replace("'", "''")
                return f"'{val_clean}'"
            if hasattr(val, 'isoformat'):
                val_str = val.isoformat().split('T')[0]
                return f"'{val_str}'"
            return f"'{str(val)}'"

        try:
            documentos_procesados = []

            for fila in filas:
                reg = dict(zip(nombres_cols_remotas, fila))
                trn_tipo = reg.get("trn_tipo")
                trn_documento = reg.get("trn_documento")
                trn_serie = reg.get("trn_serie", "WEB")
                trn_status = reg.get("trn_status")

                valores_sql = []
                for col_pg, col_db in columnas_mapa:
                    val = reg.get(col_pg, None)
                    valores_sql.append(formatear_valor_sql(val))
                
                sql_cab = f"INSERT INTO SOperacionInv ({', '.join(columnas_cab)}) VALUES ({', '.join(valores_sql)})"
                cursor_local.execute(sql_cab)

                cursor_local.execute(
                    "SELECT FTI_AUTOINCREMENT FROM SOperacionInv WHERE FTI_SERIE = ? AND FTI_TIPO = ? AND FTI_DOCUMENTO = ?",
                    (trn_serie, trn_tipo, trn_documento)
                )
                row_auto = cursor_local.fetchone()
                autoinc_generado = row_auto[0] if row_auto else 0

                cols_pg_det = [p[0] for p in columnas_mapa_det]
                cols_db_det = [p[1] for p in columnas_mapa_det if p[1].upper() not in {"FDI_AUTOINCREMENT", "FDI_BASE_AUTOINCREMENT"}]

                cursor_remoto.execute(
                    f"SELECT {', '.join(cols_pg_det)} FROM public.arc_detalletranvtas WHERE dtv_tipooperacion = %s AND dtv_documento = %s AND dtv_sync_status = false",
                    (trn_tipo, trn_documento)
                )
                filas_det = cursor_remoto.fetchall()
                nombres_cols_remotas_det = [desc[0].lower() for desc in cursor_remoto.description]

                for fila_det in filas_det:
                    reg_det = dict(zip(nombres_cols_remotas_det, fila_det))
                    valores_sql_det = []
                    for col_pg, col_db in columnas_mapa_det:
                        if col_db.upper() not in {"FDI_AUTOINCREMENT", "FDI_BASE_AUTOINCREMENT"}:
                            val_det = reg_det.get(col_pg, None)
                            valores_sql_det.append(formatear_valor_sql(val_det))

                    cols_insert_det = list(cols_db_det) + ["FDI_OPERACION_AUTOINCREMENT"]
                    valores_sql_det.append(str(autoinc_generado))

                    sql_det = f"INSERT INTO SDetalleVenta ({', '.join(cols_insert_det)}) VALUES ({', '.join(valores_sql_det)})"
                    cursor_local.execute(sql_det)

                documentos_procesados.append((trn_tipo, trn_documento, trn_status))
                contador += 1

            conn_local.commit()

            for t_tipo, t_doc, t_status in documentos_procesados:
                cursor_remoto.execute(
                    "UPDATE public.arc_transacciones SET trn_sync_status = true WHERE trn_tipo = %s AND trn_documento = %s",
                    (t_tipo, t_doc)
                )
                cursor_remoto.execute(
                    "UPDATE public.arc_detalletranvtas SET dtv_sync_status = true WHERE dtv_tipooperacion = %s AND dtv_documento = %s",
                    (t_tipo, t_doc)
                )
                
                status_guardar = t_status if t_status is not None else 4
                db_local.registrar_bajada(documento=str(t_doc), tipo=t_tipo, status_bajado=status_guardar)
                
            remoto.commit()
            
            self.logger.cerrar(f"Sincronización de bajada completada. Transacciones (Cabeceras y Detalles) insertadas: {contador}.")
            return contador
            
        except Exception as e:
            conn_local.rollback()
            remoto.rollback()
            self.logger.error(f"Error en sincronización de bajada de transacciones: {str(e)}")
            raise e
        finally:
            cursor_local.close()
            cursor_remoto.close()
            remoto.close()