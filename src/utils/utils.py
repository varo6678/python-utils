from .. import (
    cProfile,
    contextlib,
    pstats,
    pd,
    time,
    contextlib,
)

class Timing(contextlib.ContextDecorator):
    
    """
    # Usando `Timing` para medir tiempo de ejecución
    with Timing("Processing time: "):
        time.sleep(0.5)  # Simulación de un proceso que toma tiempo
        """
    
    def __init__(self, prefix="", on_exit=None, enabled=True):
        self.prefix = prefix
        self.on_exit = on_exit
        self.enabled = enabled
    
    def __enter__(self):
        self.st = time.perf_counter_ns()
    
    def __exit__(self, *exc):
        self.et = time.perf_counter_ns() - self.st
        if self.enabled:
            print(f"{self.prefix}{self.et*1e-6:6.2f} ms")


class GlobalCounters:
    
    """
    # Incrementando contadores globales
    GlobalCounters.global_ops += 1
    GlobalCounters.global_mem += 1024

    print(GlobalCounters.global_ops)  # 1
    print(GlobalCounters.global_mem)  # 1024

    # Resetear los contadores
    GlobalCounters.reset()
    print(GlobalCounters.global_ops)  # 0
    print(GlobalCounters.global_mem)  # 0
    """
    
    global_ops = 0
    global_mem = 0
    time_sum_s = 0.0
    
    @staticmethod
    def reset():
        GlobalCounters.global_ops = 0
        GlobalCounters.global_mem = 0
        GlobalCounters.time_sum_s = 0.0
        
class Profiling(contextlib.ContextDecorator):
    
    """
    import numpy as np

    def func(x: np.ndarray, verbose: bool = True):
        resultado = np.sum(x)
        if verbose: 
            print(resultado)
        return resultado

    # Crear un array aleatorio
    arr = np.random.rand(1000000)

    # Usar la clase Profiling
    with Profiling(sort='cumtime', rank=5, frac=0.2) as prof:
        func(arr)

    # Convertir los resultados a un DataFrame
    try:
        df = prof.to_dataframe()
        print(df)
    except ValueError as e:
        print(e)
    """
    
    def __init__(self, enabled=True, sort='cumtime', rank=10, frac=1.0, fn=None, ts=1):
        """
        :param enabled: Activar o desactivar el profiling.
        :param sort: El criterio de ordenación ('cumtime', 'tottime', etc.).
        :param rank: El número máximo de funciones a mostrar.
        :param frac: El porcentaje de las funciones a mostrar.
        :param fn: Nombre del archivo para almacenar los resultados si es necesario.
        :param ts: Escala de tiempo.
        """
        self.enabled = enabled
        self.sort = sort
        self.rank = rank
        self.frac = frac
        self.fn = fn
        self.time_scale = 1e3 / ts
        self.stats_data = None  # Inicializa como None
    
    def __enter__(self):
        self.pr = cProfile.Profile()
        if self.enabled:
            self.pr.enable()
        return self  # Importante: Retorna self para asignarlo a 'prof'
    
    def __exit__(self, *exc):
        if self.enabled:
            self.pr.disable()
            if self.fn:
                self.pr.dump_stats(self.fn)
            self.stats_data = pstats.Stats(self.pr).strip_dirs().sort_stats(self.sort)  # Guarda las estadísticas
            
            # Filtrar las funciones según la cantidad rank y el porcentaje frac
            func_list = self.stats_data.fcn_list
            limit = int(len(func_list) * self.frac)
            self.stats_data.print_stats(min(self.rank, limit))
    
    def to_dataframe(self):
        if self.stats_data is None:
            raise ValueError("No se encontraron datos de profiling. Asegúrate de ejecutar el bloque con el contexto de Profiling activo.")
        
        # Extraer los datos del perfilado
        rows = []
        for func, (primitive_calls, total_calls, tottime, cumtime, callers) in self.stats_data.stats.items():
            rows.append({
                "function": f"{func[2]} ({func[0]}:{func[1]})",
                "primitive_calls": primitive_calls,
                "total_calls": total_calls,
                "tottime_ms": tottime * self.time_scale,  # Convertir a milisegundos
                "cumtime_ms": cumtime * self.time_scale,  # Convertir a milisegundos
            })

        # Convertir los datos en un DataFrame de pandas
        df = pd.DataFrame(rows)
        
        # Ordenar por el criterio de ordenación (cumtime por defecto)
        df = df.sort_values(by="cumtime_ms", ascending=False)
        
        # Limitar el número de filas al parámetro rank
        return df.head(self.rank)
