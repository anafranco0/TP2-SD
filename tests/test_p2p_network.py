import subprocess
import time
import sys
import shutil
from pathlib import Path

def rodar_teste():
    print("=== Testando Rede P2P com Arquivos e Chunks Reais ===")
    
    # 1. Garante que os arquivos de teste existem
    arquivo_teste = "files/10KB.bin"
    if not Path(arquivo_teste).exists():
        print(f"Gerando arquivos de teste...")
        from tests.generete_files import generate_files
        generate_files()

    # Limpa diretórios temporários de testes anteriores
    for d in ["chunks_Peer-A", "chunks_Peer-B", "chunks_Peer-C", "reconstructed_Peer-B", "reconstructed_Peer-C"]:
        shutil.rmtree(d, ignore_errors=True)

    print("\n[*] Iniciando 3 Peers:")
    print("    - Peer-A (porta 5000): Seeder com 'files/10KB.bin'")
    print("    - Peer-B (porta 5001): Leecher conectado no Peer-A")
    print("    - Peer-C (porta 5002): Leecher conectado APENAS no Peer-B (cascata)")

    p_a = subprocess.Popen([
        sys.executable, "peer_node.py",
        "--porta", "5000",
        "--nome", "Peer-A",
        "--seeder",
        "--arquivo", arquivo_teste,
        "--metadata", "metadata_teste.json",
        "--chunk-size", "1024"
    ])
    time.sleep(1.5)

    p_b = subprocess.Popen([
        sys.executable, "peer_node.py",
        "--porta", "5001",
        "--nome", "Peer-B",
        "--metadata", "metadata_teste.json",
        "--vizinhos", "5000"
    ])
    time.sleep(1.5)

    p_c = subprocess.Popen([
        sys.executable, "peer_node.py",
        "--porta", "5002",
        "--nome", "Peer-C",
        "--metadata", "metadata_teste.json",
        "--vizinhos", "5001"
    ])

    time.sleep(6)

    print("\n[*] Encerrando os nós...")
    for p in [p_a, p_b, p_c]:
        p.terminate()
        try:
            p.wait(timeout=1)
        except Exception:
            p.kill()

    # Validação do arquivo reconstruído
    rec_b = Path("reconstructed_Peer-B/10KB.bin")
    rec_c = Path("reconstructed_Peer-C/10KB.bin")

    print("\n=== Resultado da Validação ===")
    print(f"Peer-B reconstruiu o arquivo? {'SIM' if rec_b.exists() else 'NÃO'}")
    print(f"Peer-C reconstruiu o arquivo? {'SIM' if rec_c.exists() else 'NÃO'}")

    if rec_b.exists() and rec_c.exists():
        import hashlib
        h_orig = hashlib.sha256(open(arquivo_teste, "rb").read()).hexdigest()
        h_b = hashlib.sha256(open(rec_b, "rb").read()).hexdigest()
        h_c = hashlib.sha256(open(rec_c, "rb").read()).hexdigest()
        print(f"Hash Original: {h_orig}")
        print(f"Hash Peer-B:   {h_b} ({'OK' if h_b == h_orig else 'ERRO'})")
        print(f"Hash Peer-C:   {h_c} ({'OK' if h_c == h_orig else 'ERRO'})")

if __name__ == "__main__":
    rodar_teste()

