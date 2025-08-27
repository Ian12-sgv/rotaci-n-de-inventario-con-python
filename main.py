import sys
import os
import logging
import traceback
import customtkinter as ctk
from views.main_view import MainView
from db.connection import PREDEFINED_INSTANCES, set_default_instance
from utils.helpers import export_to_excel, obtener_datos_treeview, get_save_path

# Configuración básica de loggin
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

# Función para empaquetado con PyInstaller
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def export_demo(parent, data=None):
    """
    Exporta los datos del Treeview a Excel.
    """
    if data is None:
        data = [{"Columna1": "Dato 1", "Columna2": "Dato 2"}]
    output_file = get_save_path(parent)
    if not output_file:
        logging.info("Exportación cancelada.")
        return
    try:
        export_to_excel(data, output_file)
    except Exception as e:
        logging.error("Error al exportar: %s", e)
        import tkinter.messagebox as messagebox
        messagebox.showerror("Error al exportar", f"Se produjo un error:\n{e}")
    else:
        import tkinter.messagebox as messagebox
        messagebox.showinfo("Exportación exitosa", f"Archivo guardado:\n{output_file}")

def run_view():
    """
    Lanza la aplicación principal.
    """
    # Selección automática de instancia al iniciar
    alias_default = list(PREDEFINED_INSTANCES.keys())[0]
    set_default_instance(alias_default)
    logging.debug(f"Instancia predeterminada seleccionada: {alias_default}")

    try:
        main_app = MainView(refresh_callback=lambda: None)

        main_app.mainloop()

    except Exception as e:
        logging.error("Error en la aplicación: %s", e)
        traceback.print_exc()

if __name__ == "__main__":
    run_view()
