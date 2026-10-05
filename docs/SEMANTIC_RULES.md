# Guia para explicar el analizador

## Recorrido principal

1. El IDE lee el archivo `.cps` o toma el texto del editor y lo envia a la API.
2. `Compiler` usa el lexer generado por ANTLR para reconocer tokens y guardar errores lexicos.
3. El parser generado construye el arbol y usa la recuperacion predeterminada de ANTLR.
4. `SemanticAnalyzer` recorre el arbol con un visitor y consulta la tabla de simbolos.
5. La API devuelve diagnosticos, tokens, arbol y alcances para mostrarlos en React.

El analizador no ejecuta las instrucciones del programa fuente. El arbol mostrado es
el arbol sintactico de ANTLR, con reglas y terminales.

## Partes importantes del codigo

| Archivo | Que explicar |
| --- | --- |
| `backend/analyzer/compiler.py` | Las tres fases, listeners que acumulan errores y serializacion del arbol. |
| `backend/analyzer/semantic.py` | Tipos de expresiones, firmas, resolucion de nombres, flujo y recuperacion local. |
| `backend/analyzer/symbol_table.py` | Insertar, consultar, actualizar, entrar y salir de alcances. |
| `backend/models/types.py` | Tipos simples, arreglos, identidad de clases y metadatos de simbolos. |
| `frontend/src/App.tsx` | Lectura de archivos, solicitud a la API y vistas de resultados. |
| `tests/test_rule_matrix.py` | Una pareja valida/invalida por cada regla incluida en la matriz. |
| `tests/test_regressions.py` | Ejemplos que reproducen los problemas encontrados en la revision. |

## Decisiones semanticas

- **Funciones:** una referencia a una funcion tiene tipo `function`. Su tipo de retorno
  solo se obtiene cuando se valida una llamada. Por eso `f * 2` es invalido y `f() * 2`
  puede ser valido. Las funciones anidadas resuelven nombres en sus entornos exteriores.
- **Clases:** el nombre se busca en el alcance visible; el tipo conserva una identidad
  de clase para que un nombre igual en otro bloque no cambie los miembros del objeto.
- **Herencia:** cada clase conserva el enlace a su clase base. Los recorridos guardan
  las identidades visitadas para terminar incluso si la entrada contiene un ciclo.
- **Flujo:** `break` y `continue` no pueden cruzar el limite de una funcion. Una funcion
  con retorno declarado necesita un retorno garantizado en los caminos que comprueba
  el analisis estructural de bloques, `if/else` y `try/catch`.
- **Recuperacion:** un hijo ausente o una declaracion sin nombre no detiene el visitor.
  El parser conserva su diagnostico y se revisan las sentencias posteriores.
- **Errores derivados:** un destino o miembro desconocido no genera una cadena de
  mensajes redundantes; los argumentos y otras expresiones independientes si se revisan.
- **Tokens:** las etiquetas usan el vocabulario del parser generado, que conserva los
  indices de palabras y simbolos implicitos de ANTLR.

## Limites del analisis estatico

Los indices siempre se comprueban por tipo. Tambien se detectan indices literales
negativos y accesos fuera de una longitud literal conocida. No se intenta ejecutar
expresiones para descubrir indices o longitudes dinamicas. Las longitudes se descartan
ante ramas, ciclos, llamadas y posibles alias para evitar rechazar programas validos.

La deteccion de codigo inalcanzable es estructural: detecta sentencias despues de
salidas directas y ramas que terminan en ambos lados. No demuestra si un ciclo es
infinito ni evalua condiciones constantes.

En la segunda parte, `switch` acepta valores escalares (`integer`, `float`, `string`
y `boolean`) y exige cases compatibles con el selector, siguiendo los ejemplos
del README de Compiscript. `break` puede salir de un ciclo o de un switch;
`continue` requiere un ciclo. Ninguno puede cruzar una funcion anidada.
La concatenacion de strings sigue los ejemplos del lenguaje. La gramatica incorpora
literales `float`, mencionados en los requisitos semanticos.

## Demostracion

```bash
python -m pytest -v
python quickstart.py backend
python quickstart.py frontend
```

En el IDE, abrir `valid_optional_for.cps`, `error_recovery.cps` y
`error_circular_inheritance.cps` desde `tests/test_cases/`. Revisar diagnosticos,
tokens, arbol y tabla de simbolos. Los dos archivos con errores deben terminar
y conservar diagnosticos de instrucciones posteriores al primer problema.
