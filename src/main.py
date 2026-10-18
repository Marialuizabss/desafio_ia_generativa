"""Executa a interface de entrada com Streamlit."""

import sys
from pathlib import Path


def main() -> None:
    origem = Path(__file__).resolve().parent
    if str(origem) not in sys.path:
        sys.path.insert(0, str(origem))

    from interface import renderizar

    renderizar()


def _em_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx(suppress_warning=True) is not None
    except Exception:
        return False


if __name__ == "__main__":
    if _em_streamlit():
        main()
    else:
        from streamlit.web import cli as stcli

        sys.argv = [
            "streamlit",
            "run",
            str(Path(__file__).resolve()),
            *sys.argv[1:],
        ]
        raise SystemExit(stcli.main())
