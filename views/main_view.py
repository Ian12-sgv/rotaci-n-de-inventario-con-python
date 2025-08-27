import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd

# Nota: ahora importamos get_cruce_data_df (server-side)
from db.connection import (
    get_db_connection,
    get_cruce_data_df,
    set_default_instance,
    PREDEFINED_INSTANCES,
)
from utils.helpers import export_to_excel, export_to_csv, get_save_path

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

desired_cols = [
    "CodigoBarra", "Referencia", "CodigoMarca", "Marca", "Nombre",
    "Nombre_Fabricante", "CodigoFabricante", "CategoriaCodigo", "CategoriaNombre",
    "Linea", "CantidadInicial", "Cantidad_Inicial_Agrupada", "ExistenciaActual",
    "correccion", "NumeroTransferencia", "FechaLlegada", "observacion",
    "CodigoRecibe", "Queda", "Vendido"
]

class MainView(ctk.CTk):

    def __init__(self, refresh_callback):
        super().__init__()
        self.title("Previsualización de Consulta Cruzada")
        self.geometry("900x600")
        self.refresh_callback = refresh_callback

        # Estado
        self.engine = None
        self.df_full = None    # dataset completo importado según rango
        self.df_view = None    # dataset actualmente mostrado (filtrado)

        # Layout
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_button_bar()

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.tabview.add("Cruce")
        self.cruce_frame = self.tabview.tab("Cruce")
        self._build_treeview(self.cruce_frame)

        self.filter_frame = None

    def _build_button_bar(self):
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.button_frame.grid_columnconfigure(0, weight=0)
        self.button_frame.grid_columnconfigure(1, weight=1)

        predefinidas = list(PREDEFINED_INSTANCES.keys())
        self.instancia_var = tk.StringVar(value=predefinidas[0])

        self.instancia_combo = ctk.CTkComboBox(
            self.button_frame,
            variable=self.instancia_var,
            values=predefinidas,
            command=self.on_instance_selected
        )
        self.instancia_combo.grid(row=0, column=0, sticky="w", padx=5)

        # Selecciona instancia inicial y crea engine
        self.on_instance_selected(self.instancia_var.get())

        self.import_btn = ctk.CTkButton(
            self.button_frame, text="Importar Datos", command=self.import_cruce
        )
        self.import_btn.grid(row=0, column=1, sticky="w", padx=5)

        self.export_btn = ctk.CTkButton(
            self.button_frame, text="Exportar Datos", command=self.export_data
        )
        self.export_btn.grid(row=0, column=3, sticky="w", padx=5)

        self.fecha_option = tk.IntVar(value=2)
        self.fecha_frame = ctk.CTkFrame(self.button_frame)
        self.fecha_frame.grid(row=0, column=2, sticky="e", padx=20)

        ctk.CTkLabel(self.fecha_frame, text="Filtro por fecha:").pack(anchor="w")
        ctk.CTkRadioButton(
            self.fecha_frame, text="2023/01/01 - Actual",
            variable=self.fecha_option, value=1,
            command=self.on_fecha_changed
        ).pack(anchor="w")
        ctk.CTkRadioButton(
            self.fecha_frame, text="2024/01/01 - Actual",
            variable=self.fecha_option, value=2,
            command=self.on_fecha_changed
        ).pack(anchor="w")

    def on_instance_selected(self, selected):
        try:
            set_default_instance(selected)
            self.engine = get_db_connection()
            print(f"Instancia seleccionada: {selected}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo seleccionar la instancia:\n{e}")

    def on_fecha_changed(self):
        """Reimporta automáticamente al cambiar el rango."""
        self.import_cruce()

    def _build_treeview(self, parent):
        container = tk.Frame(parent)
        container.pack(expand=True, fill="both")

        self.tree_cruce = ttk.Treeview(container, columns=desired_cols, show="headings")

        for col in desired_cols:
            self.tree_cruce.heading(col, text=col)
            self.tree_cruce.column(col, width=120, anchor="center", stretch=False)

        self.tree_cruce.grid(row=0, column=0, sticky="nsew")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree_cruce.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree_cruce.xview)
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree_cruce.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree_cruce.bind("<Button-3>", self.show_context_menu)

    def import_cruce(self):
        try:
            if not self.engine:
                self.engine = get_db_connection()
            if not self.engine:
                raise RuntimeError("No hay conexión a base de datos.")

            # Server-side import según rango seleccionado
            df = get_cruce_data_df(
                self.engine,
                fecha_option=self.fecha_option.get()
            )

            if df.empty:
                self.df_full = pd.DataFrame(columns=desired_cols)
                self.df_view = self.df_full.copy()
            else:
                # Asegura columnas esperadas
                faltan = [c for c in desired_cols if c not in df.columns]
                if faltan:
                    raise ValueError(f"Faltan columnas en el resultado SQL: {faltan}")

                self.df_full = df[desired_cols].copy()
                self.df_view = self.df_full.copy()

            self.populate_tree(self.df_view.values.tolist())
            messagebox.showinfo("Importación", "Datos importados correctamente.")

            if not self.filter_frame:
                self.create_filter_frame()

        except Exception as e:
            messagebox.showerror("Error", f"Fallo en la importación: {e}")

    def export_data(self):
        df_base = self.df_view if self.df_view is not None else self.df_full
        if df_base is None or df_base.empty:
            messagebox.showwarning("Atención", "No hay datos para exportar.")
            return

        file_path = get_save_path(self)
        if not file_path:
            return  # Usuario canceló

        try:
            columnas_texto = ["CodigoFabricante", "CategoriaCodigo", "CodigoBarra"]
            df_to_export = df_base.copy()

            for col in columnas_texto:
                if col in df_to_export.columns:
                    df_to_export[col] = df_to_export[col].astype(str).str.strip()

            if file_path.lower().endswith(".csv"):
                export_to_csv(df_to_export.to_dict(orient="records"), file_path)
            else:
                export_to_excel(df_to_export.to_dict(orient="records"), file_path)

            messagebox.showinfo("Éxito", f"Datos exportados correctamente:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Fallo al exportar:\n{e}")

    def create_filter_frame(self):
        self.label_font = ctk.CTkFont(size=11)
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        for c in range(0, 8, 2):
            self.filter_frame.grid_columnconfigure(c, weight=0)
            self.filter_frame.grid_columnconfigure(c + 1, weight=1, uniform="entry")

        def _pair(r, c, text):
            ctk.CTkLabel(self.filter_frame, text=text, font=self.label_font, height=24)\
                .grid(row=r, column=c, padx=(2, 2), pady=2, sticky="w")
            entry = ctk.CTkEntry(self.filter_frame)
            entry.grid(row=r, column=c + 1, padx=(2, 10), pady=2, sticky="ew")
            return entry

        self.codigo_barra_entry = _pair(0, 0, "Código Barra:")
        self.referencia_entry   = _pair(0, 2, "Referencia:")
        self.categoria_entry    = _pair(0, 4, "Categoría:")
        self.codigo_recibe_entry = _pair(0, 6, "Excluir CódigoRecibe(s):")

        self.linea_entry        = _pair(1, 0, "Línea:")
        self.fabrica_entry      = _pair(1, 2, "Código de Fábrica:")

        # Botones
        self.buscar_btn = ctk.CTkButton(self.filter_frame, text="Buscar", command=self.buscar_datos)
        self.buscar_btn.grid(row=2, column=6, columnspan=2, pady=(8, 0), sticky="e")

        self.limpiar_btn = ctk.CTkButton(self.filter_frame, text="Limpiar", command=self.limpiar_filtros)
        self.limpiar_btn.grid(row=2, column=4, columnspan=2, pady=(8, 0), sticky="w")

        # Enter dispara búsqueda
        for w in (
            self.codigo_barra_entry, self.referencia_entry, self.categoria_entry,
            self.codigo_recibe_entry, self.linea_entry, self.fabrica_entry
        ):
            w.bind("<Return>", lambda _e: self.buscar_datos())

    def buscar_datos(self):
        if self.engine is None:
            messagebox.showwarning("Atención", "Primero seleccione instancia e importe datos.")
            return

        # Lee filtros de la UI (sin lower: el backend normaliza Referencia)
        codigo_barra = self.codigo_barra_entry.get().strip()
        referencia   = self.referencia_entry.get().strip()
        categoria    = self.categoria_entry.get().strip()
        linea        = self.linea_entry.get().strip()
        fabrica      = self.fabrica_entry.get().strip()
        excluir_raw  = self.codigo_recibe_entry.get().strip()

        try:
            # Consulta al servidor con filtros + rango
            df = get_cruce_data_df(
                self.engine,
                codigo_filter=codigo_barra or None,
                referencia_filter=referencia or None,
                categoria_filter=categoria or None,
                linea_filter=linea or None,
                fabrica_filter=fabrica or None,
                fecha_option=self.fecha_option.get()
            )

            df = df[desired_cols].copy() if not df.empty else df

            # Exclusión de CodigoRecibe en cliente
            if excluir_raw and not df.empty:
                if "CodigoRecibe" in df.columns:
                    codigos_excluir = [c.strip().upper() for c in excluir_raw.split(",") if c.strip()]
                    temp = df.assign(CodigoRecibe=df["CodigoRecibe"].astype(str).str.strip())
                    df = temp[~temp["CodigoRecibe"].str.upper().isin(codigos_excluir)].copy()
                else:
                    messagebox.showwarning("Atención", "La columna 'CodigoRecibe' no está en los datos.")

            self.df_view = df
            self.populate_tree(self.df_view.values.tolist())

        except Exception as e:
            messagebox.showerror("Error", f"Fallo al aplicar filtros: {e}")

    def limpiar_filtros(self):
        for w in (
            self.codigo_barra_entry, self.referencia_entry, self.categoria_entry,
            self.codigo_recibe_entry, self.linea_entry, self.fabrica_entry
        ):
            w.delete(0, tk.END)

        # Reconsulta sin filtros (pero respeta el rango seleccionado)
        try:
            df = get_cruce_data_df(self.engine, fecha_option=self.fecha_option.get())
            if df.empty:
                self.df_view = pd.DataFrame(columns=desired_cols)
            else:
                self.df_view = df[desired_cols].copy()
            self.populate_tree(self.df_view.values.tolist())
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron limpiar filtros: {e}")

    def populate_tree(self, rows):
        self.tree_cruce.delete(*self.tree_cruce.get_children())
        for r in rows:
            self.tree_cruce.insert("", tk.END, values=r)

    def show_context_menu(self, event):
        row_id = self.tree_cruce.identify_row(event.y)
        col_id = self.tree_cruce.identify_column(event.x)
        if not row_id:
            return
        try:
            idx = int(col_id.lstrip("#")) - 1
        except ValueError:
            idx = 0

        values = self.tree_cruce.item(row_id, "values")
        cell = values[idx] if idx < len(values) else ""

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copiar", command=lambda: self.copy_to_clipboard(cell))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)


def dummy_refresh_function():
    return None


if __name__ == "__main__":
    app = MainView(refresh_callback=dummy_refresh_function)
    app.mainloop()
