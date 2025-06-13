import sys
import subprocess
import venv
from pathlib import Path

def create_virtualenv(venv_path):
    if not venv_path.exists():
        print(f"Criando ambiente virtual em: {venv_path}")
        venv.create(venv_path, with_pip=True)
    else:
        print("Ambiente virtual já existe.")

def install_requirements(venv_path, requirements_file):
    if sys.platform == "win32":
        pip_executable = venv_path / 'Scripts' / 'pip.exe'
    else:
        pip_executable = venv_path / 'bin' / 'pip'
        
    print("Instalando dependências...")
    # Instalando o PyInstaller separadamente e em seguida as dependências do arquivo
    subprocess.check_call(f"{str(pip_executable)} install pyinstaller", shell=True)
    comando = f"{str(pip_executable)} install --upgrade -r {str(requirements_file)}"
    try:
        subprocess.check_call(comando, shell=True)
    except subprocess.CalledProcessError as e:
        print("Erro ao instalar dependências. Detalhes:", e)
        print("\nTente executar manualmente o seguinte comando no terminal:")
        print("pip install --upgrade -r requirements.txt")
        sys.exit(1)

def update_requirements(venv_path, requirements_file):
    if sys.platform == "win32":
        pip_executable = venv_path / 'Scripts' / 'pip.exe'
    else:
        pip_executable = venv_path / 'bin' / 'pip'
        
    print("Atualizando requirements.txt com as versões instaladas (pip freeze)...")
    try:
        freeze_output = subprocess.check_output([str(pip_executable), "freeze"]).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as e:
        print("Erro ao gerar pip freeze. Detalhes:", e)
        sys.exit(1)
        
    # Filtra para remover pyinstaller (adicione mais pacotes se necessário)
    filtered_lines = [line for line in freeze_output if "pyinstaller" not in line.lower()]
    with requirements_file.open('w') as req:
        req.write("\n".join(filtered_lines) + "\n")

def build_exe(project_root):
    spec_file = project_root / "DOTformat.spec"
    print("Construindo executável a partir do spec...")
    comando = f"pyinstaller {str(spec_file)}"
    try:
        subprocess.check_call(comando, shell=True)
    except subprocess.CalledProcessError as e:
        print("Erro ao construir executável. Detalhes:", e)
        sys.exit(1)
    print("Executável gerado com sucesso!")

if __name__ == '__main__':
    # Define os caminhos do projeto
    project_root = Path(__file__).resolve().parent.parent
    venv_dir = project_root / 'env'
    requirements_txt = project_root / 'requirements.txt'
    
    create_virtualenv(venv_dir)
    install_requirements(venv_dir, requirements_txt)
    update_requirements(venv_dir, requirements_txt)
    build_exe(project_root)