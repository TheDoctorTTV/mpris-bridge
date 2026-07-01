#########################
### MODULE ENTRYPOINT ###
#########################

# Let python -m mpris_bridge behave like the installed mpris-bridge command.
from mpris_bridge.cli import main


if __name__ == "__main__":
    # Convert the CLI return code into the process exit code.
    raise SystemExit(main())
