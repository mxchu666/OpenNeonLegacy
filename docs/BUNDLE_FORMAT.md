# Bundle NEONBND2 — especificación de formato

Verificada por ingeniería inversa del launcher (`neon_legacy.exe`, 355 KB MSVC C++) y confirmada
empíricamente con extracción completa (12/12 archivos OK, tamaños exactos).

## Estructura del archivo

```
┌──────────────────────────────────────────────┐ 0x00000
│ launcher MSVC x64 (PE)                       │ ~0x54400
├──────────────────────────────────────────────┤ 0x54400  (overlay)
│ payload: entradas zstd una tras otra         │
│   [entrada 0] zstd frame  → neon.exe (538MB) │
│   [entrada 1] zstd frame  → awt.dll          │
│   ...                                        │
├──────────────────────────────────────────────┤ footer
│ tabla de entradas                            │
├──────────────────────────────────────────────┤
│ footer (80 bytes)                            │
└──────────────────────────────────────────────┘ EOF
```

## Footer (últimos 80 bytes)

| Offset | Tamaño | Campo                                                        |
|--------|--------|--------------------------------------------------------------|
| 0      | 8      | magia ASCII `NEONBND2`                                       |
| 8      | 8      | u64 LE: offset absoluto del inicio de la tabla de entradas   |
| 16     | 64     | SHA-256 hex ASCII (64 chars) — identidad del bundle          |

La tabla empieza en `footer_offset - table_len`; su longitud se deduce restando.
El campo de identidad del bundle de muestra es
`854aeefac34cce8d998c9e2b29bde8062610cf9cf0b6d491467264dfacc77838`.
Es un SHA-256 hex pero **no** coincide con hash del archivo completo ni del
payload ni de rangos obvios — el algoritmo exacto está en la decompilación del
launcher (función del error "Invalid bundle identity"). La extracción no
depende de este campo.

## Tabla de entradas

```
[u32 LE] count
entry × count:
  [u32 LE] pathLen
  [pathLen bytes] path (ASCII, charset seguro: a-z A-Z 0-9 - . _ /)
  [u64 LE] offset absoluto del frame zstd en el archivo
  [u64 LE] tamaño comprimido
  [u64 LE] tamaño descomprimido
```

Cada frame zstd es independiente (frame estándar, magia `28 B5 2F FD`).
Los offsets son contiguos: `entry[i].offset + entry[i].comp == entry[i+1].offset`.

## Contenido verificado (bundle de muestra)

| path                  | offset     | comprimido | descomprimido |
|-----------------------|-----------:|-----------:|--------------:|
| neon.exe              | 0x54400    | 266,302,080 | 537,944,064  |
| awt.dll               | 0xFE4B680  | 512,085    | 1,492,032    |
| fontmanager.dll       | 0xFEC86D5  | 330,427    | 906,320      |
| freetype.dll          | 0xFF19190  | 275,078    | 547,400      |
| java.dll              | 0xFF5C416  | 4,489      | 10,752       |
| javaaccessbridge.dll  | 0xFF5D59F  | 115,517    | 307,800      |
| javajpeg.dll          | 0xFF798DC  | 85,623     | 181,832      |
| jawt.dll              | 0xFF8E753  | 12,072     | 21,056       |
| jsound.dll            | 0xFF9167B  | 30,044     | 61,000       |
| jvm.dll               | 0xFF98BD7  | 4,107      | 9,728        |
| lcms.dll              | 0xFF99BE2  | 116,680    | 272,960      |
| lib/font-runtime.txt  | 0xFFB63AA  | 201        | 302          |

## Uso

```powershell
# extracción completa (PowerShell + 7z con soporte zstd, o zstd CLI)
tools/extract_bundle.ps1  # ver data/BUNDLE_MANIFEST.csv para offsets
```

## Notas del launcher (strings de error, útiles para parsers)

- "Missing single-file bundle footer"
- "Invalid bundle identity"
- "Invalid bundle index" / "Invalid bundle file count"
- "Invalid bundle path length" / "Unsafe bundle path"
- "Cannot create zstd decoder"
- "Cannot start extracted Neon runtime"

El launcher extrae a un "native cache" bajo `%LOCALAPPDATA%` con marcador `.ready`
y arranca el runtime extraído.
