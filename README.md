# TP2 - Transferência de Arquivos P2P (Sistemas Distribuídos)

Implementação de um sistema de transferência de arquivos Peer-to-Peer (P2P) simétrico, descentralizado e sem dependência de Tracker, desenvolvido para a disciplina de Sistemas Distribuídos do CEFET-MG.

Cada nó da rede atua simultaneamente como cliente e servidor: ele escuta pedidos de outros pares, baixa os pedaços que não tem e, assim que valida um bloco novo, já começa a repassá-lo para a rede (seeder parcial).

---

## Requisitos

- **Python 3.10 ou superior**.
- Nenhuma dependência externa precisa ser instalada (o projeto usa apenas módulos nativos: `socket`, `threading`, `hashlib`, `json`, etc.).

---

## Estrutura do Projeto

```text
TP2-SD/
├── core/
│   ├── chunk.py           # Fatiamento e manipulação de blocos
│   ├── metadata.py        # Geração e validação do metadata.json
│   ├── file_manager.py    # Leitura/escrita e validação SHA-256
│   ├── bitfield.py        # Mapa de blocos disponíveis
│   ├── protocol.py        # Mensagens P2P e enquadramento TCP (length-prefix)
│   ├── peer.py            # Motor de rede P2P (cliente, servidor e download)
│   └── storage.py         # Camada de integração entre rede e arquivos
├── files/                 # Arquivos de teste (10KB a 20MB)
├── tests/
│   ├── test_p2p_network.py     # Teste rápido de 3 nós em cascata
│   ├── benchmark_network.py    # Bateria completa da Tabela 1 do trabalho
│   └── generete_files.py       # Gerador dos arquivos de teste
├── peer_node.py           # Script principal para subir um nó no terminal
├── RELATORIO.md           # Relatório técnico completo com dados e análises
└── README.md
```

---

## Como Rodar

Você pode testar o projeto de duas formas: executando os testes prontos ou subindo cada nó manualmente em janelas de terminal separadas.

### Opção 1: Testes Automatizados (Mais rápido)

Entre na pasta do projeto:
```bash
cd TP2-SD
```

1. **Teste rápido de 3 peers (Peer A -> Peer B -> Peer C):**
   Roda em poucos segundos e mostra o nó B baixando de A e repassando dinamicamente para C:
   ```bash
   python tests/test_p2p_network.py
   ```

2. **Bateria completa dos estudos de caso (Tabela 1 do PDF):**
   Executa todas as variações de tamanho de arquivo (10KB a 20MB), blocos (1KB e 4KB) e topologias (2 e 4 peers):
   ```bash
   python tests/benchmark_network.py
   ```

---

### Opção 2: Rodando os Nós Manualmente (Terminal a Terminal)

Para simular o funcionamento real em terminais separados:

#### 1. Terminal 1 — Subir o Seeder (quem tem o arquivo original)
Ele vai fatiar o arquivo escolhido, gerar o `metadata.json` e ficar ouvindo na porta informada:
```bash
cd TP2-SD
python peer_node.py --porta 20000 --nome Peer-A --seeder --arquivo files/10KB.bin --chunk-size 1024
```

#### 2. Terminal 2 — Subir o primeiro Leecher
Ele vai ler o `metadata.json`, conectar no Peer A (porta 20000) e baixar os blocos:
```bash
cd TP2-SD
python peer_node.py --porta 20001 --nome Peer-B --vizinhos 20000
```

#### 3. Terminal 3 (Opcional) — Subir um segundo Leecher
Conecta tanto no Peer A quanto no Peer B. Assim que o Peer B receber qualquer bloco, ele também já enviará para este novo nó:
```bash
cd TP2-SD
python peer_node.py --porta 20002 --nome Peer-C --vizinhos 20000 20001
```

O arquivo baixado e remontado com hash validado será salvo automaticamente na pasta `reconstructed_<NomeDoPeer>/`.

---

## Limpeza

Os nós criam pastas de blocos temporários (`chunks_*`) e pastas de remontagem (`reconstructed_*`). Para limpar tudo antes de novos testes, basta apagar essas pastas ou rodar no PowerShell:
```powershell
Remove-Item -Recurse -Force chunks_*, reconstructed_* -ErrorAction SilentlyContinue
```
