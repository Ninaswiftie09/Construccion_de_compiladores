# Matriz de cumplimiento del proyecto 02

Se revisaron la rúbrica PDF entregada, README_TAC_GENERATION.md, el README de
Compiscript y la gramática adjunta. El PDF se llama Proyecto 02 pero su encabezado
dice Proyecto 01; sus filas evalúan generación intermedia y suman 25 puntos.
La tabla del README de generación suma 100 (25 diseño, 65 traducción, 10 símbolos).
Esta matriz cubre ambos listados; no sustituye la calificación del docente.

## Criterios de la rúbrica PDF

| Criterio | Peso sobre 25 | Implementación | Evidencia |
| --- | ---: | --- | --- |
| Diseño de CI | 3 | Compiscript TAC v1, cuádruplas y modos de dirección | TAC_DESIGN.md |
| Variables y constantes | 1 | declare, const, copy | declarations; valid_tac_logic.cps |
| Aritmética | 1 | Operadores binarios y menos unario | arithmetic; orden y precedencia |
| Lógica | 1 | not, saltos de cortocircuito | logic; short_circuit |
| Arreglos | 1 | array, load_index, length y stores | arrays; valid_tac_arrays.cps |
| Control de flujo | 3 | Etiquetas para if, ciclos, foreach y switch | casos individuales; valid_tac_control.cps |
| Funciones y parámetros | 2 | closure, param, receive, call, return | functions; llamadas anidadas |
| Recursividad | 2 | Etiquetas predeclaradas y frame por activación | recursion; valid_tac_functions.cps |
| Clases y objetos | 2 | Descriptores, inicializadores, new y receptor | classes; valid_tac_objects.cps |
| Herencia | 2 | Offsets heredados y tabla virtual sobrescrita | inheritance; inherited_layout |
| Try/catch | 2 | Pila de manejadores y salidas con limpieza | try_catch; exception_handlers |
| Reciclaje de temporales | 3 | TemporaryPool con vivos y libres | pool, 40 expresiones consecutivas |
| Tabla de símbolos | 2 | Direcciones, offsets, frames, enlaces y layouts | frame_offsets; test_symbol_table.py |

Los nombres de prueba abreviados se encuentran en `tests/test_tac.py`. La suite
usa aserciones sobre la estructura intermedia; no ejecuta Compiscript ni produce
objetos o assembler.

## Requisitos adicionales

| Requisito | Evidencia |
| --- | --- |
| Generador obligatorio de lexer y parser | ANTLR 4.13.2, Compiscript.g4 y scripts de generación |
| IDE estético para editar y compilar | React, Monaco, estilos adaptables, Ctrl+Enter |
| Selección del archivo desde la UI | Abrir .cps y arrastre; prueba de interfaz |
| Resultados y CI dentro de la UI | Diagnósticos, árbol, símbolos, TAC y tokens |
| Diagramas de imagen y previsualización | SVG en img; zoom y PNG descargable |
| Guardar imágenes dentro del proyecto | output/diagrams por solicitud; prueba de persistencia |
| Casos propios para calificación | tests/test_cases/valid_tac_*.cps y error_tac_blocked.cps |
| Reportar varios errores | Listeners de ANTLR, visitor tolerante y pruebas de recuperación |
| Evitar duplicados y ciclos de recuperación | Claves de diagnósticos, unknown y detección de herencia circular |
| No generar CI con errores | Puerta de generación y pruebas de las tres fases; sin tac.dot ni program.tac |
| Limitarse a análisis e IR | No hay intérprete, ejecución, assembler ni generador de código objeto |
| Documentación de arquitectura | ARCHITECTURE.md |
| Documentación de ejecución | README.md y SETUP.md |
| Documentación detallada del CI | TAC_DESIGN.md |
| Guía de defensa local | GUIA_DEFENSA_PROYECTO.md, excluida de Git |
| Commits en inglés por cambios | feat, test, docs y chore en el historial local |

## Condiciones para la presentación

1. Instalar las dependencias y comprobar `dot -V` antes de presentar.
2. Generar el parser con ANTLR y ejecutar las pruebas del backend y frontend.
3. Abrir un archivo válido desde la UI y mostrar las tres imágenes y el TAC.
4. Abrir error_tac_blocked.cps y mostrar varios diagnósticos y TAC bloqueado.
5. Mostrar la carpeta de imágenes y los archivos intermedios del caso válido.
6. Revisar las contribuciones reales de los tres integrantes. Los commits usan
   la identidad Git configurada; no se atribuyen artificialmente a otras personas.
7. Entregar el enlace del repositorio con estos commits. Crear commits locales
   no publica por sí solo los cambios en GitHub.
