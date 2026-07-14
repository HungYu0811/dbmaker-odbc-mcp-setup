import subprocess


class DBMakerCLI:
    """DBMaker CLI wrapper."""

    def __init__(self, config):
        self.dmsqlc_path = config.dbmaker_cli.dmsqlc_path
        self.database = config.dbmaker_cli.database


    def get_procedure_definition(self, procedure_name: str) -> str:

        command = f"""
CONNECT TO {self.database};
DEF PROCEDURE {procedure_name};
QUIT;
"""

        result = subprocess.run(
            [self.dmsqlc_path],
            input=command,
            text=True,
            capture_output=True
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        return result.stdout
