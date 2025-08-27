import os
import platform
from pathlib import Path
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import logging
from openpyxl.styles import numbers
from openpyxl.utils import get_column_letter

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def get_desktop_folder() -> str:
    if platform.system() == "Windows":
        return os.path.join(os.environ["USERPROFILE"], "Desktop")
    else:
        return str(Path.home() / "Desktop")

def get_save_path(parent, defaultextension=".xlsx", filetypes=None) -> str:
    if filetypes is None:
        filetypes = [("Archivos Excel", "*.xlsx"), ("Archivos CSV", "*.csv")]
    desktop_path = get_desktop_folder()
    file_path = filedialog.asksaveasfilename(
        parent=parent,
        title="Guardar archivo",
        initialdir=desktop_path,
        defaultextension=defaultextension,
        filetypes=filetypes
    )
    return file_path or ""

def export_to_csv(data, output_file: str) -> None:
    try:
        df = pd.DataFrame(data, columns=data[0].keys()) if data else pd.DataFrame()
        columnas_texto = ["CodigoFabricante", "CategoriaCodigo", "CodigoBarra"]
        
        # Rellenar con ceros a la izquierda en columnas específicas
        for col in columnas_texto:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.zfill(4).str.strip()
        
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logging.info("Archivo CSV guardado exitosamente en: %s", output_file)
    except Exception as e:
        logging.error("Error al exportar a CSV: %s", e)
        raise

def export_to_excel(data, output_file: str) -> None:
    try:
        df = pd.DataFrame(data, columns=data[0].keys()) if data else pd.DataFrame()
        columnas_texto = ["CodigoFabricante", "CategoriaCodigo", "CodigoBarra"]
        
        # Rellenar con ceros a la izquierda en columnas específicas
        for col in columnas_texto:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.zfill(4).str.strip()
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="Cruce", index=False)
            worksheet = writer.sheets["Cruce"]
            
            for col_name in columnas_texto:
                if col_name in df.columns:
                    col_idx = df.columns.get_loc(col_name) + 1
                    col_letter = get_column_letter(col_idx)
                    for row in range(2, len(df) + 2):
                        cell = worksheet[f"{col_letter}{row}"]
                        val = cell.value if cell.value is not None else ""
                        val_str = str(val).strip()
                        val_escaped = val_str.replace('"', '""')
                        cell.value = f'="{val_escaped}"'
                        cell.number_format = numbers.FORMAT_TEXT
        
        logging.info("Archivo Excel guardado exitosamente en: %s", output_file)
    except Exception as e:
        logging.error("Error al exportar a Excel: %s", e)
        raise

def obtener_datos_treeview(tree: ttk.Treeview) -> list:
    datos = []
    for item_id in tree.get_children():
        valores = tree.item(item_id)["values"]
        fila = dict(zip(tree["columns"], valores))
        datos.append(fila)
    return datos

def export_data_interactive(data, parent):
    formato = simpledialog.askstring("Formato exportación", "¿En qué formato desea exportar? (csv/xlsx):", parent=parent)
    if not formato:
        messagebox.showinfo("Cancelado", "No se seleccionó formato de exportación.")
        return
    formato = formato.strip().lower()
    if formato not in ("csv", "xlsx"):
        messagebox.showerror("Error", "Formato no válido. Debe ser 'csv' o 'xlsx'.")
        return

    if formato == "csv":
        filetypes = [("Archivos CSV", "*.csv")]
        def_ext = ".csv"
    else:
        filetypes = [("Archivos Excel", "*.xlsx")]
        def_ext = ".xlsx"

    file_path = get_save_path(parent, defaultextension=def_ext, filetypes=filetypes)

    if not file_path:
        messagebox.showinfo("Cancelado", "No se seleccionó ruta para guardar.")
        return

    ext = file_path.lower().split('.')[-1]
    try:
        if ext == "csv":
            export_to_csv(data, file_path)
        elif ext in ("xls", "xlsx"):
            export_to_excel(data, file_path)
        else:
            messagebox.showerror("Error", "Extensión de archivo no soportada.")
            return
        messagebox.showinfo("Éxito", f"Datos exportados correctamente a:\n{file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Error durante exportación:\n{e}")

# Ejemplo básico de UI para probar exportación

def crear_treeview_ejemplo(parent):
    columnas = ("CodigoFabricante", "CategoriaCodigo", "CodigoBarra", "Descripcion")
    tree = ttk.Treeview(parent, columns=columnas, show="headings")
    for col in columnas:
        tree.heading(col, text=col)
        tree.column(col, width=120)
    ejemplo_datos = [
        ("FAB001", "0003", "1234567890123", "Producto A"),
        ("FAB002", "0001", "2345678901234", "Producto B"),
        ("FAB003", "0009", "3456789012345", "Producto C"),
    ]
    for fila in ejemplo_datos:
        tree.insert("", tk.END, values=fila)
    tree.pack(fill=tk.BOTH, expand=True)
    return tree

def main():
    root = tk.Tk()
    root.title("Exportar datos a CSV o Excel")

    tree = crear_treeview_ejemplo(root)

    btn_exportar = tk.Button(root, text="Exportar datos", command=lambda: export_data_interactive(obtener_datos_treeview(tree), root))
    btn_exportar.pack(pady=10)

    root.geometry("600x400")
    root.mainloop()

if __name__ == "__main__":
    main()
