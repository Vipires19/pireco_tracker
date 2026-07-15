"""
CLI do Protocol Replay Lab.

Uso (a partir do diretório gateway/):

  python -m tools.replay.replay session.json
  python -m tools.replay.replay --latest
  python -m tools.replay.replay session.json --protocol GT06
  python -m tools.replay.replay --inject --protocol GT06 --hex 78780d01...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.replay.loader import SessionLoadError, SessionLoader
from tools.replay.runner import ReplayRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="replay",
        description="Protocol Replay Lab — reproduz sessões TCP gravadas no Learning Mode",
    )
    parser.add_argument(
        "session",
        nargs="?",
        help="Arquivo de sessão (.json / .jsonl) ou omitir com --latest",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Carrega a sessão mais recente em data/sessions/",
    )
    parser.add_argument(
        "--protocol",
        default=None,
        help="Força o parser (ex.: GT06). Se omitido, usa protocol_detected da sessão.",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Diretório de sessões JSONL (default: gateway/data/sessions)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Imprime o relatório em JSON",
    )
    parser.add_argument(
        "--inject",
        action="store_true",
        help="Modo Packet Injection (exige --protocol e --hex)",
    )
    parser.add_argument(
        "--hex",
        default=None,
        help="Payload hexadecimal para --inject",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runner = ReplayRunner()
    loader = SessionLoader(data_dir=args.data_dir)

    try:
        if args.inject:
            if not args.protocol or not args.hex:
                print("Erro: --inject exige --protocol e --hex", file=sys.stderr)
                return 2
            result = runner.inject(protocol=args.protocol, hex=args.hex)
            if args.as_json:
                print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            else:
                print(f"Protocol: {result.protocol}")
                print(f"Valid: {result.valid}")
                print(f"Frames: {result.frames}")
                print(f"Packet types: {', '.join(result.packet_types) or '-'}")
                print(f"ACKs: {', '.join(result.acks) or '-'}")
                if result.error:
                    print(f"Error: {result.error}")
            return 0 if result.valid else 1

        if args.latest:
            session = loader.load_latest()
        elif args.session:
            session = loader.load(args.session)
        else:
            print("Erro: informe session.json ou --latest", file=sys.stderr)
            return 2

        report = runner.replay(session, protocol=args.protocol)
        if args.as_json:
            print(report.to_json())
        else:
            print("\n".join(report.summary_lines()))
        return 0 if report.result == "MATCH" else 1

    except SessionLoadError as exc:
        print(f"Erro ao carregar sessão: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Erro no replay: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    # Garante imports de app.* quando executado como script direto.
    gateway_root = Path(__file__).resolve().parents[2]
    if str(gateway_root) not in sys.path:
        sys.path.insert(0, str(gateway_root))
    raise SystemExit(main())
