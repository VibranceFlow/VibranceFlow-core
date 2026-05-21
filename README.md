# LuminaSync

Aplicativo Windows em background que aplica perfis de cor (vibrance, brilho, contraste, gama) quando um jogo configurado está em foco, e restaura o desktop ao sair.

## Requisitos

- Windows 11 (validado na PoC)
- Python 3.11+ **64-bit**
- GPU NVIDIA desktop com Digital Vibrance no driver (opcional; GDI funciona sem NVAPI)

## Instalação rápida

```powershell
cd d:\CODES\LuminaSync
pip install -r requirements.txt
mkdir "$env:APPDATA\LuminaSync" -ErrorAction SilentlyContinue
copy profiles.json.example "$env:APPDATA\LuminaSync\profiles.json"
```

### Interface gráfica (recomendado)

```powershell
python gui_main.py
```

- **Add** — lista processos (rápida; ícone na pré-visualização ao selecionar)
- **Manual** — seleciona um `.exe` no disco
- Sliders de cor **só aparecem** ao escolher um programa na lista
- **Minimizar** → bandeja do sistema (duplo clique no ícone para abrir; **Sair** no menu encerra)
- **Fechar (X)** → encerra o aplicativo
- **Iniciar c/ Windows** → registro Run com `--tray` (abre minimizado na bandeja)

```powershell
python gui_main.py --tray
```

### Motor CLI (sem GUI)

```powershell
python main.py
```

## Perfis (`profiles.json`)

Unidades estilo Painel NVIDIA:

| Campo | Descrição |
|-------|-----------|
| `vibrance` | 0–100 (%) |
| `brightness` | offset % (ex.: `42` = +42%) |
| `contrast` | offset % |
| `gamma` | 0.4–2.8 |
| `hue` | graus 0–359 (opcional) |

## Arquitetura

Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [AGENTS.md](AGENTS.md).

```
core/
  bindings/       # GDI32 + NVAPI (ctypes)
  display_manager.py
  profile_manager.py
  window_monitor.py
  engine.py
main.py
scripts/          # PoCs históricas
```

## PoCs (validação)

```powershell
python scripts/poc_test.py
python scripts/poc_panel_color_test.py
```

Resultados: [docs/POC_FINDINGS.md](docs/POC_FINDINGS.md)

## Roadmap

[Fases 3–5 (GUI, tray, build)](docs/ROADMAP.md)
