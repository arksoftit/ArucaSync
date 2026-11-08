# ArucaSync - Sincronizador de Datos

ArucaSync es una aplicación de escritorio desarrollada en Python (con interfaz gráfica en Tkinter) diseñada para sincronizar información bidireccionalmente entre el sistema administrativo legacy **DBISAM** y la base de datos en la nube **PostgreSQL (Supabase)**. 

Esta herramienta es el puente de datos para la aplicación web de Fuerza de Ventas (desarrollada en React 18 y Node.js), permitiendo que los vendedores emitan presupuestos y pedidos en la web, y que la oficina los reciba en su sistema administrativo central.

## 🚀 Características Principales

*   **Sincronización de Subida (Up):** Extrae datos maestros (Clientes, Inventario, Vendedores, Zonas, etc.) y transacciones desde DBISAM y los inserta en PostgreSQL utilizando comandos `UPSERT`.
*   **Sincronización de Bajada (Down):** Lee los nuevos clientes y transacciones (Presupuestos y Pedidos) generados en la aplicación web y los inserta en DBISAM.
*   **Filtros Nativos:** Aplicación de reglas de negocio en el origen (ej. solo subir clientes con RIF, y solo transacciones de tipo 9 y 10).
*   **Control de Estado (`_sync_status`):** Uso de banderas booleanas en PostgreSQL para identificar qué registros están pendientes por bajar y cuáles ya fueron procesados.
*   **Cálculo Automatizado:** Delegación de cálculos de precios, impuestos y totales a Triggers de PostgreSQL, garantizando la integridad de los datos antes de bajarlos a DBISAM.

## 🛠️ Stack Tecnológico

*   **Lenguaje:** Python 3.14 (Estrictamente **32 bits**, requerido por el driver ODBC de DBISAM).
*   **Interfaz Gráfica:** Tkinter.
*   **Conectividad DBISAM:** `pyodbc` (con manejo de codificación `latin-1` para evitar truncamiento de textos).
*   **Conectividad PostgreSQL:** `pg8000.dbapi`.
*   **Base de Datos Cloud:** Supabase (PostgreSQL).

## 📁 Estructura del Proyecto

*   `main.py`: Punto de entrada de la aplicación. Contiene el menú principal (Conexiones, Subidas, Descargas).
*   `dialog_subidas.py`: Interfaz gráfica para la previsualización y ejecución de subidas hacia Supabase.
*   `dialog_descargas.py`: Interfaz gráfica para la previsualización y ejecución de bajadas desde Supabase (Clientes y Transacciones).
*   `dbconnection.py`: Gestor de conexión a la base de datos local DBISAM.
*   `remoteconnection.py`: Gestor de conexión a PostgreSQL (Supabase) y ejecución de Upserts masivos.
*   `sync_data.py`: Diccionarios de mapeo de columnas (`COLUMNAS_MAP`), mapeo de tablas (`MAPA_TABLAS`) y filtros (`FILTROS_TABLAS`).
*   `sync_down.py`: Lógica central para leer de PostgreSQL e insertar en DBISAM (manejo de llaves y recuperación de `AUTOINCREMENT`).
*   `sync_logger.py`: Módulo de creación de logs de auditoría para cada proceso de sincronización.

## ⚙️ Instalación y Configuración

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/arksoftit/ArucaSync.git
    cd ArucaSync