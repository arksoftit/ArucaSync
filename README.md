# ArucaSync - Sincronizador de Datos

ArucaSync es una aplicación de escritorio desarrollada en Python (con interfaz gráfica en Tkinter) diseñada para sincronizar información bidireccionalmente entre el sistema administrativo legacy **DBISAM** y la base de datos en la nube **PostgreSQL (Supabase)**.

Esta herramienta es el puente de datos para la aplicación web de Fuerza de Ventas (desarrollada en React 18 y Node.js), permitiendo que los vendedores emitan presupuestos y pedidos en la web, y que la oficina los reciba en su sistema administrativo central.

## 🚀 Características Principales

- **Sincronización de Subida (Up):** Extrae datos maestros (Clientes, Inventario, Vendedores, Zonas, etc.) y transacciones desde DBISAM y los inserta en PostgreSQL utilizando comandos `UPSERT`.
- **Sincronización de Bajada (Down):** Lee los nuevos clientes y transacciones (Presupuestos y Pedidos) generados en la aplicación web y los inserta en DBISAM.
- **Filtros Nativos:** Aplicación de reglas de negocio en el origen (ej. solo subir clientes con RIF, y solo transacciones de tipo 9 y 10).
- **Control de Estado (`_sync_status`):** Uso de banderas booleanas en PostgreSQL para identificar qué registros están pendientes por bajar y cuáles ya fueron procesados.
- **Cálculo Automatizado:** Delegación de cálculos de precios, impuestos y totales a Triggers de PostgreSQL, garantizando la integridad de los datos antes de bajarlos a DBISAM.

## 🛠️ Stack Tecnológico

- **Lenguaje:** Python 3.14 (Estrictamente **32 bits**, requerido por el driver ODBC de DBISAM).
- **Interfaz Gráfica:** Tkinter.
- **Conectividad DBISAM:** `pyodbc` (con manejo de codificación `latin-1` para evitar truncamiento de textos).
- **Conectividad PostgreSQL:** `pg8000.dbapi`.
- **Base de Datos Cloud:** Supabase (PostgreSQL).

## 📁 Estructura del Proyecto

- `main.py`: Punto de entrada de la aplicación. Contiene el menú principal (Conexiones, Subidas, Descargas).
- `dialog_subidas.py`: Interfaz gráfica para la previsualización y ejecución de subidas hacia Supabase.
- `dialog_descargas.py`: Interfaz gráfica para la previsualización y ejecución de bajadas desde Supabase (Clientes y Transacciones).
- `dbconnection.py`: Gestor de conexión a la base de datos local DBISAM.
- `remoteconnection.py`: Gestor de conexión a PostgreSQL (Supabase) y ejecución de Upserts masivos.
- `sync_data.py`: Diccionarios de mapeo de columnas (`COLUMNAS_MAP`), mapeo de tablas (`MAPA_TABLAS`) y filtros (`FILTROS_TABLAS`).
- `sync_down.py`: Lógica central para leer de PostgreSQL e insertar en DBISAM (manejo de llaves y recuperación de `AUTOINCREMENT`).
- `sync_logger.py`: Módulo de creación de logs de auditoría para cada proceso de sincronización.

## ⚙️ Instalación y Configuración

1. **Clonar el repositorio:**

```bash
git clone https://github.com/arksoftit/ArucaSync.git
cd ArucaSync
```

1. **Crear y activar el entorno virtual (usando Python de 32 bits):**

```bash
python -m venv .venv
source .venv/Scripts/activate
```

1. **Instalar dependencias:**

```bash
pip install -r requirements.txt
```

1. **Configuración de Credenciales:**

- En la carpeta `config/`, asegúrate de tener los archivos `conexiones.json` (para DBISAM) y `remotedb.json` (para Supabase).
- *Nota: Estos archivos contienen credenciales sensibles y no deben subirse al repositorio público.*

## 💻 Uso

1. Ejecuta la aplicación:

```bash
python sync/main.py
```

1. Configura las conexiones desde el menú **Conexiones**.
1. Usa el menú **Subidas** para enviar los datos de DBISAM a la nube.
1. Usa el menú **Descargas** para visualizar los registros pendientes y transferirlos a DBISAM.

## 📝 Notas de Desarrollo y Soluciones Implementadas

- **Truncamiento de Textos:** Se detectó y solucionó un problema donde los textos largos (nombres de clientes) se cortaban al bajarlos a DBISAM. Se ajustó la lógica de formateo para evitar falsos positivos con la letra 'T' y se forzó la codificación `latin-1` en `pyodbc`.
- **Manejo de AUTOINCREMENT:** DBISAM rechaza la inyección de valores manuales altos en campos `AUTOINC`. La aplicación deja que DBISAM genere el ID y recupera el valor insertado usando `SELECT MAX(...)` para vincular las cabeceras con sus detalles.
- **Campos BLOB/Memo:** Los campos binarios (LONGVARBINARY) se omiten en el mapeo ya que no son necesarios para la integración.
- **Triggers en PostgreSQL:** Se implementaron funciones para que la base de datos calcule automáticamente los montos, subtotales e impuestos al momento de la inserción, evitando que el frontend o el backend web envíen datos erróneos.

---

## 📅 Registro de Actualizaciones (Changelog)

### Actualización: 08 de Noviembre de 2026

En esta sesión se implementaron las siguientes mejoras y reglas de negocio en la base de datos PostgreSQL (Supabase) para consolidar la integración con el sistema administrativo:

- **Máscara de Documentos de 12 Dígitos:** Las transacciones generadas por la aplicación web ahora utilizan un formato de número de documento compuesto por el año y mes (`YYYYMM`) más un correlativo de 6 dígitos (Ej: `202611000015`).
- **Nuevos Triggers en PostgreSQL:** Se crearon dos funciones y sus respectivos Triggers para automatizar la nomenclatura sin afectar el código de Node.js:
  - `trg_aplicar_prefijo_documento`: Captura el número crudo enviado a `arc_transacciones` y le concatena el prefijo `YYYYMM`.
  - `trg_heredar_documento_detalle`: Asegura que los detalles en `arc_detalletranvtas` hereden exactamente el mismo número de documento formateado de su cabecera.
- **Estandarización de Estatus:** Basado en el diccionario de datos oficial de DBISAM, se corrigió el estatus de las transacciones web. Ahora se insertan con estatus `4` (**Tránsito**) en lugar de `1` (Procesada), indicando que están pendientes de revisión por la oficina administrativa.
- **Validación de Flujo Completo:** Se comprobó con éxito que la nueva nomenclatura de 12 dígitos viaja correctamente desde PostgreSQL y se inserta sin truncamientos ni errores en los campos `FTI_DOCUMENTO` y `FDI_DOCUMENTO` de DBISAM.

*Desarrollado para optimizar el flujo de trabajo entre la fuerza de ventas y el sistema administrativo.*
