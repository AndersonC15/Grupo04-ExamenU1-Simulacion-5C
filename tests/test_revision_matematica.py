"""Oráculos independientes para la revisión matemática y la regresión científica."""
import math
from pathlib import Path
import subprocess
import sys
import types
import unittest
from model.teoria import TeoriaMMc
from model.simulador import SimuladorMMc


class RevisionMatematica(unittest.TestCase):
    def test_erlang_c_independiente_y_conversion_de_unidades(self):
        teoria=TeoriaMMc()
        for c in range(1,21):
            for rho in (0.1,0.6,0.95,0.999):
                mu=0.8
                llegadas=rho*c*mu
                a=llegadas/mu
                termino=a**c/(math.factorial(c)*(1-rho))
                p0=1/(sum(a**n/math.factorial(n) for n in range(c))+termino)
                lq=termino*p0*rho/(1-rho)
                r=teoria.calcular(llegadas,mu,c)
                self.assertAlmostEqual(r['rho'],rho)
                self.assertTrue(math.isclose(r['Lq'],lq,rel_tol=1e-10,abs_tol=1e-10))
                self.assertAlmostEqual(r['Wq'],r['Lq']/llegadas)
                horas=teoria.calcular(llegadas*60,mu*60,c)
                self.assertTrue(math.isclose(r['Wq']/60,horas['Wq'],rel_tol=1e-10,abs_tol=1e-10))
        for c in (1,3,20):
            for rho in (1,1.2):
                r=teoria.calcular(rho*c,1,c)
                self.assertFalse(r['estable'])
                self.assertIsNone(r['Wq'])

    def test_resultados_cientificos_conservados_respecto_main(self):
        raiz=Path(__file__).resolve().parent.parent
        try:
            fuente=subprocess.check_output(['git','show','main:model/simulador.py'],cwd=raiz,text=True,stderr=subprocess.DEVNULL)
        except (FileNotFoundError,subprocess.CalledProcessError):
            self.skipTest('Regresión histórica disponible en el checkout con la rama main.')
        modulo=types.ModuleType('baseline_mmc')
        exec(compile(fuente,'main:model/simulador.py','exec'),modulo.__dict__)
        for tipo in ('unica','multiples'):
            for cajas in (1,3):
                for semilla in (0,42):
                    p=dict(llegadas=1.5,servicio=0.8,cajas=cajas,duracion=50,semilla=semilla,organizacion=tipo)
                    actual=SimuladorMMc().simular(**p)
                    anterior=modulo.SimuladorMMc().simular(**p)
                    for clave in ('L','Lq','W','Wq','rho','P0','llegados','atendidos','pendientes'):
                        self.assertAlmostEqual(actual[clave],anterior[clave],places=10)
                    for a,b in zip(actual['clientes'],anterior['clientes']):
                        for clave in ('id','caja','llegada','inicio','salida','espera','servicio','estancia'):
                            self.assertEqual(a[clave],b[clave])

    def test_python_optimizado_no_elimina_operaciones_de_cola(self):
        codigo='from model.simulador import SimuladorMMc; [print(SimuladorMMc().simular(1,2,2,10,organizacion=t)["pendientes_cola"]) for t in ("unica","multiples")]'
        resultado=subprocess.check_output([sys.executable,'-O','-c',codigo],text=True)
        self.assertEqual(resultado.strip(),'0\n0')
