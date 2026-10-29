"""Punto de entrada del simulador de supermercado M/M/c."""
import tkinter as tk
from controller.controlador import ControladorSimulacion
from view.ventana import VentanaPrincipal


def main():
    raiz = tk.Tk()
    vista = VentanaPrincipal(raiz)
    ControladorSimulacion(vista)
    raiz.mainloop()


if __name__ == '__main__':
    main()
