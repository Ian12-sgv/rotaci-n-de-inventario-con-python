import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from db.connection import get_db_connection, get_cruce_data, set_default_instance, PREDEFINED_INSTANCES

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

desired_cols = [
    "CodigoBarra", "Referencia", "CodigoMarca", "Marca", "Nombre",
    "Nombre_Fabricante", "CodigoFabricante", "CategoriaCodigo", "CategoriaNombre",
    "Linea", "CantidadInicial", "Cantidad_Inicial_Agrupada", "ExistenciaActual",
    "correccion", "NumeroTransferencia", "FechaLlegada", "observacion", "Queda", "Vendido"
]

class MainView(ctk.CTk):

    def __init__(self, refresh_callback):
        super().__init__()
        self.title("Previsualización de Consulta Cruzada")
        self.geometry("900x600")
        self.refresh_callback = refresh_callback
        self.df_cruce = None

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

    # ---------------------------- helpers ---------------------------------

    def _recalc_visible_totals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Recalcula:
        - Cantidad_Inicial_Agrupada = suma de CantidadInicial por CodigoBarra SOLO con las filas visibles (df).
        - Queda, Vendido = porcentajes usando ese nuevo denominador visible.
        No modifica tus filtros; solo ajusta columnas calculadas para lo que se muestra.
        """
        if df.empty:
            return df

        # Asegurar tipos numéricos (evita problemas con strings)
        if "CantidadInicial" in df.columns:
            df["CantidadInicial"] = pd.to_numeric(df["CantidadInicial"], errors="coerce").fillna(0)
        else:
            df["CantidadInicial"] = 0

        if "ExistenciaActual" in df.columns:
            df["ExistenciaActual"] = pd.to_numeric(df["ExistenciaActual"], errors="coerce").fillna(0)
        else:
            df["ExistenciaActual"] = 0

        # Suma visible por CodigoBarra
        if "CodigoBarra" in df.columns:
            tot_visible = df.groupby("CodigoBarra")["CantidadInicial"].transform("sum")
        else:
            # Si no existiera (no debería), usa suma global
            tot_visible = pd.Series(df["CantidadInicial"].sum(), index=df.index)

        # Actualiza la columna con el total visible
        df["Cantidad_Inicial_Agrupada"] = tot_visible

        # Recalcular Queda/Vendido con ese denominador visible
        denom = tot_visible.replace(0, pd.NA)
        queda_num = ((df["ExistenciaActual"] * 100) / denom).astype("float")
        queda_num = queda_num.fillna(0).round(2)
        vendido_num = (100 - queda_num).round(2)

        # Formato con coma y %
        df["Queda"] = queda_num.map(lambda x: f"{x:.2f}%".replace(".", ","))
        df["Vendido"] = vendido_num.map(lambda x: f"{x:.2f}%".replace(".", ","))

        return df

    # ---------------------------- UI --------------------------------------

    def _build_button_bar(self):
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.button_frame.grid_columnconfigure(0, weight=0)
        self.button_frame.grid_columnconfigure(1, weight=1)

        # Cargar solo las instancias predefinidas
        predefinidas = list(PREDEFINED_INSTANCES.keys())
        self.instancia_var = tk.StringVar(value=predefinidas[0])

        self.instancia_combo = ctk.CTkComboBox(
            self.button_frame,
            variable=self.instancia_var,
            values=predefinidas,
            command=self.on_instance_selected
        )
        self.instancia_combo.grid(row=0, column=0, sticky="w", padx=5)

        # Forzar selección al iniciar
        self.on_instance_selected(self.instancia_var.get())

        # Botón «Importar Datos»
        self.import_btn = ctk.CTkButton(
            self.button_frame, text="Importar Datos", command=self.import_cruce
        )
        self.import_btn.grid(row=0, column=1, sticky="w", padx=5)

        # Selector de rango de fechas
        self.fecha_option = tk.IntVar(value=2)
        self.fecha_frame = ctk.CTkFrame(self.button_frame)
        self.fecha_frame.grid(row=0, column=2, sticky="e", padx=20)

        ctk.CTkLabel(self.fecha_frame, text="Filtro por fecha:").pack(anchor="w")
        ctk.CTkRadioButton(
            self.fecha_frame, text="2023/01/01 - Actual", variable=self.fecha_option, value=1
        ).pack(anchor="w")
        ctk.CTkRadioButton(
            self.fecha_frame, text="2024/01/01 - Actual", variable=self.fecha_option, value=2
        ).pack(anchor="w")

    def on_instance_selected(self, selected):
        try:
            set_default_instance(selected)
            print(f"Instancia seleccionada: {selected}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo seleccionar la instancia:\n{e}")

    def _build_treeview(self, parent):
        container = tk.Frame(parent)
        container.pack(expand=True, fill="both")

        self.tree_cruce = ttk.Treeview(container, columns=desired_cols, show="headings")
        for col in desired_cols:
            self.tree_cruce.heading(col, text=col)
            self.tree_cruce.column(col, width=120, anchor="center", stretch=True)

        self.tree_cruce.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree_cruce.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree_cruce.xview)
        self.tree_cruce.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        container.bind("<Configure>", self._auto_resize_columns)
        self.tree_cruce.bind("<Button-3>", self.show_context_menu)

    def _auto_resize_columns(self, event):
        total = event.width
        col_w = max(90, int(total / len(desired_cols)))
        for col in desired_cols:
            self.tree_cruce.column(col, width=col_w)

    def create_filter_frame(self):
        self.label_font = ctk.CTkFont(size=11)
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        for c in range(0, 6, 2):
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

        self.linea_entry        = _pair(1, 0, "Línea:")
        self.fabrica_entry      = _pair(1, 2, "Código de Fábrica:")

        # ✅ NUEVO: checkbox "Solo corrección = 0"
        self.correccion_cero_var = tk.IntVar(value=0)
        self.correccion_cero_chk = ctk.CTkCheckBox(
            self.filter_frame,
            text="Solo corrección = 0",
            variable=self.correccion_cero_var
        )
        self.correccion_cero_chk.grid(row=1, column=4, columnspan=2, padx=(2, 10), pady=2, sticky="w")

        self.buscar_btn = ctk.CTkButton(
            self.filter_frame, text="Buscar", command=self.buscar_datos
        )
        self.buscar_btn.grid(row=2, column=0, columnspan=6, pady=(8, 0), sticky="e")

    # ---------------------------- data flow --------------------------------

    def import_cruce(self):
        try:
            engine = get_db_connection()
            data = get_cruce_data(engine, fecha_option=self.fecha_option.get())
            df = pd.DataFrame(data) if data else pd.DataFrame()

            # Recalcular totales para el conjunto visible actual (todo el dataset)
            df = self._recalc_visible_totals(df.copy())

            # Mantener solo las columnas deseadas
            self.df_cruce = df[desired_cols].copy() if not df.empty else df
            self.populate_tree(self.df_cruce.values.tolist())

            messagebox.showinfo("Importación", "Datos importados correctamente.")

            if not self.filter_frame:
                self.create_filter_frame()

        except Exception as e:
            messagebox.showerror("Error", f"Fallo en la importación: {e}")

    def buscar_datos(self):
        if self.df_cruce is None:
            messagebox.showwarning("Atención", "Primero importe los datos.")
            return

        df = self.df_cruce.copy()
        filtros = {
            "CodigoBarra": self.codigo_barra_entry.get().strip(),
            "Referencia": self.referencia_entry.get().strip().lower(),
            "CategoriaNombre": self.categoria_entry.get().strip().lower(),
            "Linea": self.linea_entry.get().strip().lower(),
            "CodigoFabricante": self.fabrica_entry.get().strip(),
            "CorreccionCero": bool(self.correccion_cero_var.get()),
        }

        if "CodigoBarra" in df.columns and filtros["CodigoBarra"]:
            df = df[df["CodigoBarra"].astype(str) == filtros["CodigoBarra"]]
        if "Referencia" in df.columns and filtros["Referencia"]:
            df = df[df["Referencia"].astype(str).str.strip().str.lower() == filtros["Referencia"]]
        if "CategoriaNombre" in df.columns and filtros["CategoriaNombre"]:
            df = df[df["CategoriaNombre"].astype(str).str.strip().str.lower() == filtros["CategoriaNombre"]]
        if "Linea" in df.columns and filtros["Linea"]:
            df = df[df["Linea"].astype(str).str.strip().str.lower() == filtros["Linea"]]
        if "CodigoFabricante" in df.columns and filtros["CodigoFabricante"]:
            df = df[df["CodigoFabricante"].astype(str).str.strip() == filtros["CodigoFabricante"]]

        if filtros["CorreccionCero"] and "correccion" in df.columns:
            mask = pd.to_numeric(df["correccion"], errors="coerce") == 0
            df = df[mask]

        # 🔁 Recalcular totales (agrupada/porcentajes) con SOLO estas filas visibles
        df = self._recalc_visible_totals(df.copy())

        # Mantener columnas en el orden esperado
        df = df.reindex(columns=desired_cols)

        self.populate_tree(df.values.tolist())

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

# -------------------------------------------------------------------------
def dummy_refresh_function():
    return None

if __name__ == "__main__":
    app = MainView(refresh_callback=dummy_refresh_function)
    app.mainloop()
