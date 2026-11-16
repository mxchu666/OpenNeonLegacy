# Obfuscación — veredicto y evidencia

## Respuesta corta

**Ni ZKM ni JNIC.** No hay ningún ofuscador de bytecode en este build porque
**no existe bytecode que ofuscar**: la compilación AOT de GraalVM destruyó el
bytecode antes de que cualquier ofuscador de `.class` pudiera actuar. Los
deobfuscators de bytecode (zkm-deobfuscator, JnicDeobfuscator) no tienen
entrada válida contra este artefacto: no hay jar ni `.class` en él.

## Por qué la pregunta no aplica a este artefacto

ZKM (Zelix KlassMaster) y JNIC son ofuscadores de **bytecode**: operan sobre
archivos `.class` dentro de un jar. La cadena del artefacto es:

```
neon_legacy.exe = launcher MSVC (355 KB) + bundle NEONBND2 (267.8 MB, zstd)
  └── 12 archivos: imagen nativa GraalVM (538 MB) + DLLs JVM/AWT
        └── .text 125 MB (métodos compilados a x86-64) + .svm_hea 411 MB (heap)
```

`native-image` compila cada método a código máquina y descarta el bytecode.
El manifiesto firmado embebido (2,509 entradas) lista los **nombres**, no el
código. No hay un solo `.class` real en el binario.

## Evidencia (escaneo del heap completo, 411 MB)

| Marcador | Resultado | Naturaleza de los hits |
|---|---|---|
| `Zelix` (nombre del vendor ZKM) | **0** | — |
| `ZKM` como constante de string | **0** | 20 hits = bytes aleatorios dentro de streams comprimidos (PNG IDAT / zstd), no strings Java |
| `JNIC` / `jnic` constantes | **0** | 2+12 hits = tabla JNI estándar de GraalVM (`com.oracle.svm.core.jni.functions.JNIInvocationInterface$Exports$JNICreateJavaVMPrologue_*`) y el topónimo polaco "Wojnicz" en locales |
| `PK\x03\x04` / `PK\x01\x02` (firma zip) | **0 archivos** | 3+3 hits = constantes inmediatas en el código x86-64 AOT de zip4j (`cmp` contra el magic), no archivos zip |
| `CA FE BA BE` (magic de .class) | **0 archivos** | 2 hits = inmediatos en código AOT (chequeos de carga de clases), no estructuras de class file |

Además, las dos únicas firmas de zip son el código compilado de zip4j —
la misma evidencia que ya descarta un jar embebido (ver
`docs/BUNDLE_FORMAT.md`).

## Lo que sí hay (y cómo se deobfusca)

1. **Re-obfuscación de nombres con el diccionario vanilla.** 2,507 de las
   2,509 clases del manifest = el client.jar oficial 1.8.9 de Mojang, clase
   a clase (`data/NEON_CLASS_DIFF.txt`: 0 añadidas, 0 eliminadas). ZKM o
   JNIC habrían roto ese 1:1 (renombrado único, encriptación de strings y
   flow que dejaría el diff irreconocible). Deobfuscación de nombres:
   `data/DEOBF_CLASS_MAP.csv` (MCP 9.19, obf → `net.minecraft.*`).
2. **Strings de Neon en claro** (auth, storage, `neonRawMouseInput`, etc.).
   Un string-encryptor (ZKM StringEncryption / JNIC) los habría dejado
   cifrados en el heap; están legibles.
3. **Estructura navegable**: `decompiled/java-skeletons/` — 1,614 esqueletos
   top-level con nombre real MCP + 895 inner classes listadas en su clase
   padre (`tools/dump_class_skeletons.py`, índice por paquete en
   `_index.md`).
4. **Cuerpos de métodos**: único camino real es el trabajo AOT manual
   (IDA/Ghidra sobre `.text`), anclado por el mapa de clases y las
   constantes del heap — guía en `decompiled/README.md`. No existe
   herramienta "GraalVM decrypter" que devuelva `.java` desde código AOT:
   el bytecode ya no está en ninguna parte.

## Si aparece un jar de Neon Legacy en el futuro

Builds no-AOT o un runtime real con bytecode sí aplicarían: identificar
ZKM vs JNIC por marcadores del jar (strings `Zelix`/`zkm`, patrones de
encriptación de strings, natives de JNIC) y correr el deobfuscator
correspondiente antes del mapa MCP. Contra este artefacto no hay nada que
alimentar.
