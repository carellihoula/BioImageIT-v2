import os
import subprocess
from pathlib import Path
from typing import List, Optional
import platform
import datetime
import tarfile
import urllib.request
import stat

class EnvironmentManager:
    def __init__(self, envs_dir: str = "micromamba"):
        self.base_dir = Path(envs_dir) 
        self.root_prefix = self.base_dir.parent / "micromamba_root"
        self.micromamba_path = self.base_dir / "bin" / "micromamba"
        self.envs_dir = self.root_prefix / "envs"
        self.envs_dir.mkdir(parents=True, exist_ok=True)

        self._ensure_micromamba()

    def _ensure_micromamba(self):
        if self.micromamba_path.exists():
            return  # micromamba already installed

        print("micromamba not found, downloading...")

        system = platform.system()
        machine = platform.machine()

        if system == "Windows":
            # For Windows: download micromamba.exe binary
            url = "https://github.com/mamba-org/micromamba-releases/releases/download/2.0.4-0/micromamba-win-64.exe"
            dest = self.base_dir / "bin" / "micromamba.exe"
            dest.parent.mkdir(parents=True, exist_ok=True)
            print(f"Downloading micromamba for Windows from {url}")
            urllib.request.urlretrieve(url, dest)
            self.micromamba_path = dest

        elif system in ["Linux", "Darwin"]:
            # Linux/macOS: download tar archive and extract
            sys_name = "linux" if system == "Linux" else "osx"
            arch = "64" if machine == "x86_64" else machine

            url = f"https://micro.mamba.pm/api/micromamba/{sys_name}-{arch}/latest"
            print(f"Downloading micromamba from {url}")

            self.base_dir.mkdir(parents=True, exist_ok=True)
            archive_path = self.base_dir / "micromamba.tar.bz2"

            urllib.request.urlretrieve(url, archive_path)

            # Extract micromamba/bin/micromamba binary
            with tarfile.open(archive_path, "r:bz2") as tar:
                member = tar.getmember("bin/micromamba")
                tar.extract(member, path=self.base_dir)

            # Remove archive
            archive_path.unlink()

            # Move micromamba to ./micromamba/bin/micromamba (for uniformity)
            extracted_path = self.base_dir / "bin" / "micromamba"
            extracted_path.chmod(extracted_path.stat().st_mode | stat.S_IXUSR)  # make executable

            self.micromamba_path = extracted_path

        else:
            raise Exception(f"Unsupported platform: {system}")

        print(f"micromamba downloaded and ready at {self.micromamba_path}")

    def _get_log_path(self, env_name: str) -> Path:
        log_dir = self.base_dir / "logs" / env_name
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "environment.log"

    def _log(self, env_name: str, message: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = self._get_log_path(env_name)
        with open(log_path, "a") as f:
            f.write(f"[{timestamp}] {message}\n")

    def _run(self, args: List[str], env_name: str, capture_output: bool = False):
        full_cmd = [self.micromamba_path] + args + ["--root-prefix", str(self.root_prefix)]
        # self._log(env_name, f"RUN: {' '.join(full_cmd)}")
        self._log(env_name, f"RUN: {' '.join(map(str, full_cmd))}")

        try:
            result = subprocess.run(
                full_cmd,
                check=True,
                text=True,
                capture_output=capture_output
            )
            if capture_output:
                self._log(env_name, f"STDOUT: {result.stdout.strip()}")
                self._log(env_name, f"STDERR: {result.stderr.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            self._log(env_name, f"ERROR: {e.stderr.strip() if e.stderr else str(e)}")
            raise

    def create(self, name: str, dependencies: dict):
        """
        dependencies = {
            "python": "3.10",
            "conda": ["code-server"],
            "pip": ["napari[all]"]
        }
        """
        self._log(name, f"Creating environment '{name}'")
        create_args = [
            "create", "-y", "-n", name,
            f"python={dependencies.get('python', '3.10')}"
        ] + dependencies.get("conda", [])

        self._run(create_args, env_name=name)

        if dependencies.get("pip"):
            self._log(name, f"Installing pip dependencies: {dependencies['pip']}")
            self.run(name, ["pip", "install"] + dependencies["pip"])

        self._log(name, f"Environment '{name}' created successfully.")

    def exists(self, name: str) -> bool:
        result = subprocess.run(
            [self.micromamba_path, "env", "list", "--json", "--root-prefix", str(self.root_prefix)],
            capture_output=True, text=True
        )
        import json
        envs = json.loads(result.stdout).get("envs", [])
        return any(name in Path(env).name for env in envs)

    def run(self, name: str, command: List[str]):
        self._log(name, f"Running short command in '{name}': {' '.join(command)}")
        return self._run(["run", "-n", name] + command, env_name=name, capture_output=True)

    def launch(self, name: str, custom_command: str):
        """
        Launch a long-running process inside the environment.
        """
        log_path = self._get_log_path(name)
        self._log(name, f"Launching long process: {custom_command}")
        command = [
            self.micromamba_path,"--root-prefix" , str(self.root_prefix),
            "run", "-n", name, "bash", "-c", custom_command,   
        ]
        with open(log_path, "a") as log_file:
            subprocess.Popen(command, stdout=log_file, stderr=log_file)

        self._log(name, "Process launched.")

environmentManager = EnvironmentManager()

