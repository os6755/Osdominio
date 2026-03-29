import os
import sys
import time
import json
import re
import asyncio
import threading
import select
import datetime
import subprocess
import importlib.util
from datetime import timedelta, timezone

NOME = 'TeleCombos v1.0'
if sys.platform.startswith('win'):
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW(NOME)
else:
    sys.stdout.write(f'\033]2;{NOME}\007')

if sys.version_info < (3, 7):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\033[91m" + "="*50)
    print(" [ERRO CRITICO] VERSAO DO PYTHON INCOMPATIVEL")
    print("="*50 + "\033[0m")
    print("\nVoce esta usando uma versao muito antiga do Python.")
    print("Este script exige recursos modernos (Asyncio/Telethon) do Python 3.7+.")
    print("\n\033[93mAMBIENTES RECOMENDADOS:\033[0m")
    print("1. Termux")
    print("2. Pydroid 3")
    print("\n\033[91mAplicativos antigos como QPython 3.6.6 NAO sao compativeis.\033[0m")
    print("O script sera encerrado para evitar travamentos.")
    sys.exit(1)

def verificar_instalar_dependencias():
    libs = ["telethon", "rich"]
    precisa_reiniciar = False

    for lib in libs:
        if importlib.util.find_spec(lib) is None:
            print(f"\033[93m[!] Biblioteca '{lib}' nao encontrada. Instalando...\033[0m")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
                precisa_reiniciar = True
            except Exception as e:
                print(f"\033[91m[ERROR] Falha ao instalar {lib}: {e}\033[0m")
                sys.exit(1)
    
    if precisa_reiniciar:
        print("\033[92m[OK] Dependencias instaladas. Reiniciando o script...\033[0m")
        time.sleep(2)
        os.execv(sys.executable, [sys.executable] + sys.argv)

verificar_instalar_dependencias()

try:
    from telethon import TelegramClient, errors
    from telethon.tl.types import DocumentAttributeFilename
    from telethon.errors import SessionPasswordNeededError
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    from rich.table import Table
    from rich.align import Align
    from rich import box
    from rich.console import Console, Group
    from rich.markdown import Markdown
    from telethon.tl.types import InputMessagesFilterDocument, InputMessagesFilterUrl
except ImportError:
    print("Erro critico nas importacoes. Reinicie o aplicativo.")
    sys.exit(1)

try:
    import termios
    import tty
except ImportError:
    pass

console = Console()

BASE_FOLDER = "/sdcard/TelegramCombos"
CONFIG_FILE = os.path.join(BASE_FOLDER, "config.json")

def restaurar_terminal():
    if sys.stdin.isatty():
        try:
            fd = sys.stdin.fileno()
            attr = termios.tcgetattr(fd)
            attr[3] = attr[3] | termios.ECHO | termios.ICANON
            termios.tcsetattr(fd, termios.TCSADRAIN, attr)
        except:
            pass

class KeyMonitor:
    def __init__(self):
        self.stop_event = threading.Event()
        self.key_pressed = None
        self.old_settings = None

    def start(self):
        if sys.stdin.isatty():
            try:
                self.old_settings = termios.tcgetattr(sys.stdin)
                threading.Thread(target=self._monitor, daemon=True).start()
            except: pass

    def _monitor(self):
        try:
            tty.setcbreak(sys.stdin.fileno())
            while not self.stop_event.is_set():
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    if key.lower() == 's':
                        self.key_pressed = 's'
                        self.stop_event.set()
        except: pass
        finally:
            self.restore()

    def stop(self):
        self.stop_event.set()
        self.restore()

    def restore(self):
        if self.old_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            except: pass
        restaurar_terminal()

def limpar():
    os.system('cls' if os.name == 'nt' else 'clear')
    sys.stdout.write("\033c")
    sys.stdout.flush()

def banner():
    limpar()

    ascii_art = r""" _____    _       ___           _
|_   _|__| |___  / __|___ _ __ | |__  ___ ___
  | |/ -_) / -_) | (__/ _ \ '  \| '_ \/ _ (_-<
  |_|\___|_\___|  \___\___/_|_|_|_.__/\___/__/
"""
    
    art_content = Text(ascii_art, style="bold #F4A460")

    content_group = Group(
        Align.center(art_content),
    )

    painel_interno = Panel(
        content_group,
        border_style="#00FF7F", 
        box=box.HEAVY,
        padding=(0, 0),
        expand=True
    )

    subtitle_text = Text.from_markup("[#FFD700][ ᴅᴇsᴇɴᴠᴏʟᴠɪᴅᴏ ᴘᴏʀ ᴍᴀʀʟᴏɴ ]")        

    painel_externo = Panel(
        painel_interno,
        title_align="center",
        border_style="#9370DB",
        subtitle=subtitle_text,
        subtitle_align="center",
        expand=True,
        box=box.HEAVY,
        padding=(0, 0)
    )

    console.print(painel_externo)
    console.print()
def input_seguro(texto, padrao=""):
    restaurar_terminal()
    console.print(texto, end="")
    try:
        sys.stdout.flush()
        i = input("")
        return i.strip() if i.strip() else padrao
    except:
        return padrao

def carregar_config():
    if not os.path.exists(BASE_FOLDER):
        os.makedirs(BASE_FOLDER)
    padrao = {
        "tg_api_id": 35372790, 
        "tg_api_hash": "fe1e572d43e8a413f5a908d171720bab",
        "last_phone": None,
        "turbo_mode": False
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                dados = json.load(f)
                padrao.update(dados)
        except: pass
    salvar_config(padrao)
    return padrao

def salvar_config(dados):
    with open(CONFIG_FILE, 'w') as f: json.dump(dados, f, indent=4)

def obter_sessao_automatica():
    conf = carregar_config()
    last = conf.get('last_phone')
    files = [f for f in os.listdir(BASE_FOLDER) if f.endswith('.session')]
    
    if last:
        nome_sessao = f"{last}.session"
        caminho = os.path.join(BASE_FOLDER, nome_sessao)
        if os.path.exists(caminho):
            return caminho
    
    if not files:
        console.print("[red]Nenhuma conta encontrada. Adicione uma conta no menu Gerenciar Contas.[/red]")
        time.sleep(2)
        return None

    banner()
    console.print("[bold cyan]--- SELECIONE A CONTA ---[/bold cyan]")
    for i, f in enumerate(files, 1): 
        console.print(f"[{i}] {f.replace('.session', '')}")
    
    console.print("[red][V] Voltar[/red]")
    escolha = input_seguro("\n[bold red]» Escolha: [/bold red]", "1")
    
    if escolha.lower() == 'v': return None
    
    try:
        idx = int(escolha) - 1
        nome_arquivo = files[idx]
        caminho = os.path.join(BASE_FOLDER, nome_arquivo)
        
        conf['last_phone'] = nome_arquivo.replace('.session', '')
        salvar_config(conf)
        
        return caminho
    except: return None

async def configurar_e_rodar_scan(client, alvos_iniciais=None):
    conf = carregar_config()
    turbo = conf.get('turbo_mode', False)

    CONCURRENCY_LIMIT = 60 if turbo else 23
    CHUNK_SIZE = 65536 if turbo else 4096

    dados = {'srv': set(), 'cmb': set(), 'm3u': set()}
    fingerprints = set()
    stats_total = {'srv': 0, 'cmb': 0, 'm3u': 0}
    stats = {'msg':0, 'txt':0, 'skip':0, 'bytes': 0} 
    
    rex_url = re.compile(r'http[s]?://\S+')
    rex_login = re.compile(r'username=([^&"\s]+)&password=([^&"\s]+)')
    rex_host = re.compile(r'(http[s]?://[^/]+)')

    MAX_FILE_SIZE = 15 * 1024 * 1024

    def norm(u):
        u = u.strip().rstrip('/')
        if u.endswith(':8080'): return u[:-5]
        elif u.endswith(':80'): return u[:-3]
        return u

    monitor = KeyMonitor()
    total_grupos_conta = 0

    if not alvos_iniciais:
        console.print("\n[green]Carregando grupos da conta...[/green]")
        dialogs = []
        try:
            async for d in client.iter_dialogs(limit=None):
                if d.is_group or d.is_channel: dialogs.append(d)
        except: pass
        
        total_grupos_conta = len(dialogs)
        banner()
        console.print(f"[bold cyan]--- SELEÇÃO DE GRUPOS ({len(dialogs)}) ---[/bold cyan]")
        
        for i, d in enumerate(dialogs, 1):
            nome = getattr(d, 'name', 'Sem Nome')
            if len(nome) > 35: nome = nome[:32] + "..."
            console.print(f"[white][{i}] {nome}[/white]")

        console.print(f"[yellow][T] TODOS os grupos[/yellow]")
        console.print("[red][V] Voltar[/red]")
        
        sel = input_seguro("\n[bold red]» Escolha (ex: 1,3 ou T): [/bold red]", "T")
        if sel.lower() == 'v': return
        
        alvos = []
        if sel.lower() == 't': alvos = dialogs
        else:
            try:
                indices = [int(x.strip()) for x in sel.split(',') if x.strip().isdigit()]
                alvos = [dialogs[i-1] for i in indices if 0 <= i-1 < len(dialogs)]
            except: pass
        if not alvos: alvos = dialogs
    else:
        alvos = alvos_iniciais
        total_grupos_conta = len(alvos)

    banner()
    console.print(f"[green]Grupos Selecionados: {len(alvos)}[/green]")
    if turbo:
        console.print("[bold red blink]🚀 MODO TURBO ATIVADO 🚀[/bold red blink]")
    else:
        console.print("[bold green]🛡️ MODO SEGURO ATIVADO[/bold green]")
    
    console.print("\n[bold cyan]--- NOME PERSONALIZADO ---[/bold cyan]")
    op_nome = input_seguro("[green]Deseja salvar com nome personalizado? (S/N) ou V p/ Voltar: [/green]", "N").lower()
    if op_nome == 'v': return

    nome_personalizado = None
    if op_nome == 's':
        nome_personalizado = input_seguro("[cyan]Digite o nome (sem .txt): [/cyan]").strip()
        if not nome_personalizado: nome_personalizado = None
    
    console.print("\n[bold cyan]--- O QUE DESEJA SALVAR? 💾 ---[/bold cyan]")
    console.print("[green][1] Apenas Servidores[/green]\n[yellow][2] Apenas Links M3U[/yellow]")
    console.print("[red][3] Apenas Combos (User:Pass)[/red]\n[white][4] Extrair TUDO (Recomendado)[/white]")
    console.print("[red][V] Voltar[/red]")
    opt = input_seguro("\n[bold red]» Opção: [/bold red]", "4")
    if opt.lower() == 'v': return
    
    sv_srv = opt in ['1','4']; sv_m3u = opt in ['2','4']; sv_cmb = opt in ['3','4']

    console.print("\n[bold cyan]--- PERÍODO DE BUSCA 🗓️ ---[/bold cyan]")
    console.print("[1] 7 Dias\n[2] 15 Dias\n[3] 30 Dias\n[4] 60 Dias\n[5] 90 Dias\n[6] 120 Dias\n[7] Tudo\n[8] Data Personalizada")
    console.print("[red][V] Voltar[/red]")
    d = input_seguro("\n[bold red]» Opção: [/bold red]", "3")
    if d.lower() == 'v': return
    
    date_range = None
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if d=='1': date_range = {'start': now - timedelta(days=7), 'end': now}
    elif d=='2': date_range = {'start': now - timedelta(days=15), 'end': now}
    elif d=='3': date_range = {'start': now - timedelta(days=30), 'end': now}
    elif d=='4': date_range = {'start': now - timedelta(days=60), 'end': now}
    elif d=='5': date_range = {'start': now - timedelta(days=90), 'end': now}
    elif d=='6': date_range = {'start': now - timedelta(days=120), 'end': now}
    elif d=='8':
        while True:
            try:
                console.print("\n[bold cyan]--- DATA PERSONALIZADA ---[/bold cyan]")
                console.print("[red][V] Voltar[/red]")
                data_inicio_str = input_seguro("[cyan]Data inicial (dd/mm/aaaa): [/cyan]")
                if data_inicio_str.lower() == 'v': return

                data_fim_str = input_seguro("[cyan]Data final (dd/mm/aaaa): [/cyan]")
                if data_fim_str.lower() == 'v': return
                
                data_inicio = datetime.datetime.strptime(data_inicio_str, "%d/%m/%Y")
                data_fim = datetime.datetime.strptime(data_fim_str, "%d/%m/%Y")
                
                data_inicio = data_inicio.replace(tzinfo=timezone.utc)
                data_fim = data_fim.replace(tzinfo=timezone.utc)
                data_fim = data_fim.replace(hour=23, minute=59, second=59)
                
                if data_inicio > data_fim:
                    console.print("[red]Data inicial não pode ser maior que data final![/red]")
                    continue
                
                date_range = {'start': data_inicio, 'end': data_fim}
                break
            except: console.print("[red]Formato inválido! Use dd/mm/aaaa[/red]")
    
    if not date_range: date_range = {'start': None, 'end': None}

    console.print("\n[bold cyan]--- MODO DE LEITURA 🔍 ---[/bold cyan]")
    console.print("[1] Ler apenas Mensagens de Texto\n[2] Baixar e Ler Arquivos (.txt)\n[3] Ambos (Completo)")
    console.print("[red][V] Voltar[/red]")
    mod = input_seguro("\n[bold red]» Opção: [/bold red]", "3")
    if mod.lower() == 'v': return

    do_txt = mod in ['1','3']; do_file = mod in ['2','3']

    start = time.time()
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    def parse(text):
        found = False
        for link in rex_url.findall(text):
            if "username=" in link:
                try:
                    creds = rex_login.search(link)
                    host = rex_host.search(link)
                    if creds and host:
                        u, p = creds.group(1), creds.group(2)
                        h_raw = host.group(1)
                        h_norm = norm(h_raw)                            
                        fp = f"{u}:{p}@{h_norm}"
                        
                        if sv_srv: stats_total['srv'] += 1
                        if sv_cmb: stats_total['cmb'] += 1
                        if sv_m3u: stats_total['m3u'] += 1
                        
                        if fp not in fingerprints:
                            if sv_srv: dados['srv'].add(h_norm)
                            if sv_cmb: dados['cmb'].add(f"{u}:{p}")
                            if sv_m3u: dados['m3u'].add(f"{h_norm}/get.php?username={u}&password={p}&type=m3u_plus")
                            fingerprints.add(fp)
                            found = True
                except: pass
        return found

    async def download_worker(msg):
        async with semaphore:
            try:
                preview = b''
                async for chunk in client.iter_download(msg.document, request_size=CHUNK_SIZE):
                    preview += chunk
                    if len(preview) >= 20480: break
                
                decoded_preview = preview.decode('utf-8', 'ignore')
                if 'username=' not in decoded_preview and 'http' not in decoded_preview: return

                content = await msg.download_media(file=bytes)
                if content:
                    stats['bytes'] += len(content)

                if parse(content.decode('utf-8', 'ignore')): pass
                stats['txt'] += 1
            except: pass

    def gerar_painel_progresso(grupo_atual, grupo_idx, total_grupos):
        elap = time.time() - start
        mins, secs = divmod(int(elap), 60)
        
        # Cálculo da Velocidade e MB
        speed = int(stats['msg'] / elap) if elap > 0 else 0
        mb_downloaded = stats['bytes'] / (1024 * 1024)
        
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(justify="left")
        
        grid.add_row(Align.center("[bold orange1 on black]>>> [S] PARA PARAR E SALVAR <<<[/]"))
        grid.add_row("")
        
        grid.add_row(f"[bold white]📂 Grupo Atual:[/]")
        nome_safe = grupo_atual[:30] + "..." if len(grupo_atual) > 35 else grupo_atual
        grid.add_row(f"[yellow]{nome_safe} ({grupo_idx}/{total_grupos})[/]")
        
        grid.add_row(f"[bold white]⏱️ Tempo Decorrido:[/][yellow] {mins:02}:{secs:02}[/]")
        grid.add_row(f"[bold white]⚡Velocidade Atual:[/][cyan] {speed} msg/s[/]")
        
        grid.add_row("[dim]" + "─" * 25 + "[/]")
        
        grid.add_row(f"[white]📨 Mensagens Lidas:   [/][cyan]{stats['msg']:,}[/]")
        grid.add_row(f"[white]📄 Arquivos Baixados: [/][cyan]{stats['txt']:,}[/]")
        grid.add_row(f"[white]💾 Dados Processados: [/][cyan]{mb_downloaded:.1f} MB[/]")
        grid.add_row(f"[white]⏭️ Grupos Pulados:    [/][red]{stats['skip']}[/]")
        
        grid.add_row("[dim]" + "─" * 25 + "[/]")
        
        grid.add_row(f"[green]🟢 Links M3U:          {len(dados['m3u']):,}[/]")
        grid.add_row(f"[cyan]🔵 Combos Encontrados: {len(dados['cmb']):,}[/]")
        grid.add_row(f"[magenta]🟣 Servidores Únicos:  {len(dados['srv']):,}[/]")
        
        t_style = "[bold red] TURBO 🚀 [/]" if turbo else "[green] SEGURO 🛡️ [/]"
        return Panel(
            grid, 
            style="green", 
            border_style="#EEE8AA", 
            title=f"[bold green]SCANNER TELEGRAM ({t_style})[/]",
            subtitle="[#B8860B]ʙʏ ᴍᴀʀʟᴏɴ[/#B8860B]"
        )

    banner()
    monitor.start()
    
    with Live(gerar_painel_progresso("Iniciando...", 0, len(alvos)), refresh_per_second=12, console=console) as live:
        for idx, grp in enumerate(alvos, 1):
            if monitor.key_pressed == 's': break
            
            nome_grp = getattr(grp, 'name', 'Grupo')
            
            tem_conteudo = False
            try:
                if do_file:
                    res = await client.get_messages(grp, limit=1, filter=InputMessagesFilterDocument)
                    if res.total > 0: tem_conteudo = True
                if not tem_conteudo and do_txt:
                    res = await client.get_messages(grp, limit=1, filter=InputMessagesFilterUrl)
                    if res.total > 0: tem_conteudo = True
                
                if not tem_conteudo:
                    stats['skip'] += 1
                    continue 
            except: pass

            streak = 0
            download_tasks = []

            try:
                async for msg in client.iter_messages(grp):
                    if monitor.key_pressed == 's': break
                    
                    if date_range['start'] and msg.date < date_range['start']: break
                    if date_range['end'] and msg.date > date_range['end']: continue
                    
                    stats['msg'] += 1
                    hit = False
                    
                    if do_txt and msg.text:
                        if parse(msg.text): hit = True
                    
                    if do_file and msg.document:
                        is_valid = False
                        if hasattr(msg.document, 'attributes'):
                            for attr in msg.document.attributes:
                                if isinstance(attr, DocumentAttributeFilename):
                                    if attr.file_name.lower().endswith(('.txt', '.m3u', '.cfg')):
                                        is_valid = True
                        
                        if is_valid and msg.document.size < MAX_FILE_SIZE:
                            hit = True
                            download_tasks.append(download_worker(msg))
                    
                    if hit: streak = 0
                    else: streak += 1
                    
                    if len(download_tasks) >= (60 if turbo else 20):
                        await asyncio.gather(*download_tasks)
                        download_tasks = []
                        live.update(gerar_painel_progresso(nome_grp, idx, len(alvos)))

                    if streak >= 600:
                        stats['skip'] += 1
                        break
                    
                    if stats['msg'] % 20 == 0:
                        live.update(gerar_painel_progresso(nome_grp, idx, len(alvos)))
                
                if download_tasks: await asyncio.gather(*download_tasks)

            except: pass
            live.update(gerar_painel_progresso(nome_grp, idx, len(alvos)))
    
    monitor.stop()

    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    dirs = {'Srv': 'Servidores', 'Cmb': 'Combos', 'M3u': 'M3u'}
    for k,v in dirs.items(): os.makedirs(os.path.join(BASE_FOLDER, v), exist_ok=True)
    
    total_seconds = int(time.time() - start)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    tempo_total_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    mb_final = stats['bytes'] / (1024 * 1024)
    speed = stats['msg'] / total_seconds if total_seconds > 0 else 0

    banner()
    tb_res = Table(title="RELATÓRIO FINAL", box=box.ROUNDED)
    tb_res.add_column("Métrica", style="cyan")
    tb_res.add_column("Valor", style="white")
    
    tb_res.add_row("Tempo Decorrido", tempo_total_str)
    tb_res.add_row("Grupos Escaneados", f"{len(alvos)} / {total_grupos_conta}")
    tb_res.add_row("Mensagens Lidas", f"{stats['msg']:,}")
    tb_res.add_row("Velocidade Média", f"{int(speed)} msg/s")
    tb_res.add_row("Arquivos TXT Baixados", f"{stats['txt']:,}")
    tb_res.add_row("Dados Processados", f"{mb_final:.1f} MB")
    tb_res.add_row("Grupos Pulados", f"{stats['skip']}")
    
    sc = 0
    if dados['srv']:
        dup = stats_total['srv'] - len(dados['srv'])
        if nome_personalizado:
            p = os.path.join(BASE_FOLDER, 'Servidores', f"{nome_personalizado}_Servidores.txt")
        else:
            p = os.path.join(BASE_FOLDER, 'Servidores', f"Servers_{len(dados['srv'])}_{ts}.txt")
        with open(p, 'w') as f: f.write('\n'.join(sorted(dados['srv'])))
        tb_res.add_row("Servidores Salvos", f"[green]{len(dados['srv']):,}[/green] (Dup -{dup:,})")
        sc+=1
        
    if dados['cmb']:
        import random 
        dup = stats_total['cmb'] - len(dados['cmb'])
        if nome_personalizado:
            p = os.path.join(BASE_FOLDER, 'Combos', f"{nome_personalizado}_Combos.txt")
        else:
            p = os.path.join(BASE_FOLDER, 'Combos', f"Combo_{len(dados['cmb'])}_{ts}.txt")

        lista_randomica = list(dados['cmb'])
        random.shuffle(lista_randomica)
        with open(p, 'w') as f: f.write('\n'.join(lista_randomica))
        tb_res.add_row("Combos Salvos", f"[green]{len(dados['cmb']):,}[/green] (Dup -{dup:,})")
        sc+=1

    if dados['m3u']:
        dup = stats_total['m3u'] - len(dados['m3u'])
        if nome_personalizado:
            p = os.path.join(BASE_FOLDER, 'M3u', f"{nome_personalizado}_M3u.txt")
        else:
            p = os.path.join(BASE_FOLDER, 'M3u', f"M3u_{len(dados['m3u'])}_{ts}.txt")
        with open(p, 'w') as f: f.write('\n'.join(sorted(dados['m3u'])))
        tb_res.add_row("M3U Salvos", f"[green]{len(dados['m3u']):,}[/green] (Dup -{dup:,})")
        sc+=1

    console.print(tb_res)
    if sc == 0: console.print("\n[red]Nenhum dado novo encontrado para salvar.[/red]")
    else: console.print(f"\n[yellow]Arquivos salvos em: {BASE_FOLDER}[/yellow]")
    input_seguro("\n[bold yellow]Enter para voltar...[/bold yellow]")

def menu_config_api():
    conf = carregar_config()
    while True:
        banner()
        console.print(Panel(f"[white]ID Atual:[/white] [yellow]{conf['tg_api_id']}[/yellow]\n[white]Hash Atual:[/white] [yellow]{conf['tg_api_hash']}[/yellow]", title="[cyan]CONFIGURAÇÃO API[/cyan]", border_style="cyan"))
        console.print("\n[green][1] Alterar Dados da API[/green]")
        console.print("[green][2] Restaurar Padrão[/green]")
        console.print("[red][0] Voltar ao Menu Principal[/red]")
        
        op = input_seguro("\n[bold red]» Escolha: [/bold red]", "0")
        
        if op == '1':
            novo_id = input_seguro("\n[yellow]Novo API ID (ou V para voltar): [/yellow]")
            if novo_id.lower() == 'v': return
            
            novo_hash = input_seguro("[yellow]Novo API HASH (ou V para voltar): [/yellow]")
            if novo_hash.lower() == 'v': return

            if novo_id.isdigit() and len(novo_hash) > 10:
                conf['tg_api_id'] = int(novo_id); conf['tg_api_hash'] = novo_hash
                salvar_config(conf); console.print("\n[bold green]Salvo![/bold green]"); time.sleep(1)
            else: console.print("\n[bold red]Inválido.[/bold red]"); time.sleep(1)
        elif op == '2':
            conf['tg_api_id'] = 35372790; conf['tg_api_hash'] = "fe1e572d43e8a413f5a908d171720bab"
            salvar_config(conf); console.print("\n[bold green]Restaurado![/bold green]"); time.sleep(1)
        elif op == '0': break

def menu_configuracoes():
    while True:
        conf = carregar_config()
        turbo_ativo = conf.get('turbo_mode', False)

        status_turbo = "[bold red blink]ATIVADO 🚀[/]" if turbo_ativo else "[green]DESATIVADO (Seguro)[/]"
        
        banner()
        console.print(Panel(
            f"[white]Modo Turbo:[/white] {status_turbo}\n",
            title="[cyan]CONFIGURAÇÕES DE PERFORMANCE[/cyan]",
            border_style="cyan"
        ))
        
        if turbo_ativo:
            console.print("\n[yellow][1] Desativar Modo Turbo (Voltar ao Seguro)[/yellow]")
        else:
            console.print("\n[yellow][1] Ativar Modo Turbo (Rápido)[/yellow]")
            
        console.print("[red][0] Voltar[/red]")
        
        op = input_seguro("\n[bold red]» Escolha: [/bold red]", "0")
        
        if op == '1':
            if not turbo_ativo:
                console.print("\n[bold red on white]!!! ATENÇÃO - RISCO DE FLOOD !!![/bold red on white]")
                console.print("[red]O uso do Modo Turbo aumenta o risco de FloodWait.[/red]")
                console.print("[red]Recomendado apenas para scans curtos ou com API própria.[/red]")
                confirma = input_seguro("\n[yellow]Deseja ativar mesmo assim? (S/N): [/yellow]", "N")
                if confirma.lower() == 's':
                    conf['turbo_mode'] = True
                    salvar_config(conf)
                    console.print("\n[green]Modo Turbo ATIVADO![/green]")
            else:
                conf['turbo_mode'] = False
                salvar_config(conf)
                console.print("\n[green]Modo Seguro ATIVADO![/green]")
            time.sleep(1)
            
        elif op == '0': break
def menu_tutorial():
    while True:
        banner()
        
        texto_tutorial = """
[bold orange1]1. COMO CONECTAR (LOGIN)[/bold orange1]
[white]• Vá no menu [bold cyan][4] Gerenciar Contas[/] e escolha [bold green][A] Adicionar[/].
• Digite seu número com o código do país e DDD.
  [dim]Exemplo:[/dim] [bold green]+5511999999999[/]
• O código de acesso chegará no seu [bold]APLICATIVO DO TELEGRAM[/] (não é SMS).
• [bold red]Atenção:[/bold red] Se você usa "Verificação em Duas Etapas" (senha na nuvem), o script pedirá essa senha logo após você digitar o código de 5 dígitos.[/white]

[bold orange1]2. COMO RESOLVER ERROS (DATABASE LOCKED)[/bold orange1]
[white]• Se aparecer o erro vermelho [bold red]"sqlite3.OperationalError: database is locked"[/]:
  Isso ocorre quando o script anterior não fechou corretamente e travou o arquivo.
  [bold green]SOLUÇÃO:[/bold green]
  1. Vá em [bold cyan][4] Gerenciar Contas[/].
  2. Use a opção [bold red][D] Deletar Conta[/] e apague a sessão travada.
  3. Faça o login novamente do zero.
  • Se o erro persistir, reinicie o seu celular ou force a parada do Termux/Pydroid.[/white]

[bold orange1]3. COMO CRIAR E TROCAR SUA API (PASSO A PASSO)[/bold orange1]
[white]• A API padrão funciona, mas usar uma própria é mais rápido.
  1. Acesse o site oficial: [u blue]https://my.telegram.org[/]
  2. Digite seu número, clique em Next e insira o código que chegará no seu Telegram.
  3. Clique na primeira opção: [bold cyan]API Development Tools[/].
  4. Vai aparecer um formulário. Preencha exatamente assim:
     - [bold]App title:[/] Coloque qualquer nome (Ex: [green]MeuScanV1[/])
     - [bold]Short name:[/] Um apelido curto (Ex: [green]meuscan[/])
     - [bold]URL:[/] Pode colocar [dim]http://google.com[/] ou deixar vazio.
     - [bold]Platform:[/] Selecione [green]Android[/].
     - [bold]Description:[/] Pode deixar em branco.
  5. Clique no botão azul [bold blue]Create Application[/] no final.
  6. Uma nova tela abrirá. Copie estes dois dados:
     - [bold yellow]App api_id[/] (São apenas números)
     - [bold yellow]App api_hash[/] (É um código longo de letras e números)
  7. Volte no script, vá em [bold yellow][5] Configurações API[/] > [bold green][1] Alterar[/] e cole seus dados.[/white]

[bold orange1]4. ESTRUTURA DE ARQUIVOS (ONDE SALVA?)[/bold orange1]
[white]• Todos os resultados ficam na pasta interna: [bold]/sdcard/TelegramCombos[/]
  • [bold magenta]Pasta Servidores:[/] Contém listas limpas apenas com URLs (DNS).
  • [bold green]Pasta M3u:[/] Contém as listas completas com usuário e senha.
  • [bold cyan]Pasta Combos:[/] Contém apenas o formato Usuário:Senha.
• O script remove duplicatas automaticamente antes de salvar.[/white]

[bold orange1]5. MODOS DE EXTRAÇÃO (QUAL USAR?)[/bold orange1]
[white]• [bold green]Iniciar Extração (Geral):[/] Busca todos os servidores, combos e M3U de todos os grupos.
• [bold blue]Extração Servidor Alvo:[/] Filtra a busca por servidores específicos que você informa, ideal para encontrar combos de um servidor específico.
• [bold yellow]Buscar Grupos:[/] Busca grupos por nome para facilitar a seleção.
• [bold magenta]Data Personalizada:[/] Nova opção que permite especificar um período exato para o scan (ex: 13/11/2025 a 06/12/2025).
• [bold red]Nome Personalizado:[/] Você pode salvar os arquivos com um nome personalizado antes de iniciar o scan.
• [bold white]Extrair TUDO:[/] Recomendado! Salva os 3 formatos de uma vez.[/white]

[bold orange1]6. SESSÃO AUTOMÁTICA[/bold orange1]
[white]• O script agora memoriza a última conta utilizada para agilizar o processo.
• Ao iniciar uma extração ou busca, ele entrará [bold]automaticamente[/bold] na conta padrão.
• Para trocar a conta utilizada, vá em [bold cyan][4] Gerenciar Contas[/] e use a opção [bold blue][P] Definir Conta Padrão[/].[/white]

[bold orange1]7. MODO TURBO & PERFORMANCE[/bold orange1]
[white]• Disponível no menu [bold red][6] Configurações[/].
• [bold green]Modo Seguro (Padrão):[/] Velocidade moderada, ideal para evitar bloqueios e rodar por longos períodos.
• [bold red]Modo Turbo:[/] Aumenta drasticamente a velocidade de download e leitura de arquivos, ideal para scans curtos.
• [bold yellow]Atenção:[/] O uso excessivo do Turbo pode causar "FloodWait". Use com sabedoria e moderação![/white]
"""
        
        console.print(Panel(
            texto_tutorial.strip(),
            title="[bold white on blue] GUIA OFICIAL & AVANÇADO TELECOMBOS [/]",
            border_style="blue",
            padding=(1, 1)
        ))

        input_seguro("\n[bold yellow]Pressione Enter para voltar ao Menu Principal...[/bold yellow]")
        break

def menu_sessoes():
    conf = carregar_config()
    api_id = conf['tg_api_id']
    api_hash = conf['tg_api_hash']
    
    while True:
        banner()
        console.print("[bold cyan]--- GERENCIAR CONTAS ---[/bold cyan]")
        console.print(f"[dim]Conta Padrão Atual: {conf.get('last_phone', 'Nenhuma')}[/dim]")
        
        files = [f for f in os.listdir(BASE_FOLDER) if f.endswith('.session')]
        
        if not files: console.print("[red](Nenhuma conta logada)[/red]")
        else:
            for i, f in enumerate(files, 1): 
                marcador = "*" if f.replace('.session', '') == conf.get('last_phone') else " "
                console.print(f"[white][{i}] {f.replace('.session', '')} [green]{marcador}[/green][/white]")
        
        console.print("\n[green][A] Adicionar Nova Conta[/green]")
        console.print("[blue][P] Definir Conta Padrão[/blue]")
        console.print("[red][D] Deletar Conta[/red]")
        console.print("[yellow][V] Voltar ao Menu Principal[/yellow]")
        
        op = input_seguro("\n[bold red]» Opção: [/bold red]", "V").lower()
        
        if op == 'v': break
        
        elif op == 'p':
            if not files: continue
            console.print("[red][V] Cancelar[/red]")
            num = input_seguro("\n[bold blue]Número da conta para ser padrão: [/bold blue]")
            if num.lower() == 'v': continue
            if num.isdigit():
                idx = int(num) - 1
                if 0 <= idx < len(files):
                    novo_padrao = files[idx].replace('.session', '')
                    conf['last_phone'] = novo_padrao
                    salvar_config(conf)
                    console.print(f"[green]Conta padrão alterada para: {novo_padrao}[/green]")
                    time.sleep(1)

        elif op == 'a':
            banner()
            console.print("[bold cyan]--- ADICIONAR CONTA ---[/bold cyan]")
            console.print("[red][V] Voltar ao Menu Principal[/red]")
            
            phone = input_seguro("\n[cyan]Digite o número (+55...) ou V p/ Sair: [/cyan]")
            if phone.lower() == 'v': return
            if not phone: continue
            
            console.print(f"\n[white]Número:[/white] [yellow]{phone}[/yellow]")
            confirma = input_seguro("[red]O número está correto? [S/N] (ou V para sair): [/red]", "S").lower()
            
            if confirma == 'v': return
            if confirma != 's': continue
            
            nome_final = phone.replace('+', '').replace(' ', '')
            caminho_final = os.path.join(BASE_FOLDER, nome_final)
            caminho_temp = os.path.join(BASE_FOLDER, "temp_login")
            
            client = TelegramClient(
                caminho_temp, 
                api_id, 
                api_hash, 
                device_model="TeleCombos", 
                system_version="Android 15", 
                app_version="1.0", 
                lang_code="pt-br", 
                system_lang_code="pt-br"
            )
            
            async def login_flow():
                try:
                    console.print("\n[yellow]Conectando...[/yellow]")
                    await client.connect()
                    
                    if not await client.is_user_authorized():
                        console.print("[yellow]Enviando código...[/yellow]")
                        await client.send_code_request(phone)
                        
                        code = input_seguro("[cyan]Código (ou V para cancelar): [/cyan]")
                        if code.lower() == 'v': return False
                        
                        try:
                            await client.sign_in(phone, code)
                        except SessionPasswordNeededError:
                            pw = input_seguro("[cyan]Senha 2FA (ou V para cancelar): [/cyan]")
                            if pw.lower() == 'v': return False
                            await client.sign_in(password=pw)
                    return True
                except Exception as e:
                    console.print(f"\n[bold red]Erro: {e}[/bold red]")
                    return False
                finally:
                    await client.disconnect()

            sucesso = client.loop.run_until_complete(login_flow())
            
            if sucesso:
                if os.path.exists(f"{caminho_temp}.session"):
                    if os.path.exists(f"{caminho_final}.session"): os.remove(f"{caminho_final}.session")
                    os.rename(f"{caminho_temp}.session", f"{caminho_final}.session")
                    
                    conf['last_phone'] = nome_final
                    salvar_config(conf)
                    
                    console.print("\n[bold green]Login Salvo com Sucesso![/bold green]")
            else:
                if os.path.exists(f"{caminho_temp}.session"): os.remove(f"{caminho_temp}.session")
                console.print("\n[bold red]Operação cancelada ou falha.[/bold red]")
            
            time.sleep(2)

        elif op == 'd':
            if not files: continue
            banner()
            console.print("[red]--- DELETAR CONTA ---[/red]")
            for i, f in enumerate(files, 1): console.print(f"[white][{i}] {f.replace('.session', '')}[/white]")
            
            console.print("\n[red][V] Voltar ao Menu Principal[/red]")
            num = input_seguro("\n[bold red]Número para apagar: [/bold red]")
            if num.lower() == 'v': return
            
            if num.isdigit():
                idx = int(num) - 1
                if 0 <= idx < len(files):
                    try: 
                        nome_removido = files[idx].replace('.session', '')
                        os.remove(os.path.join(BASE_FOLDER, files[idx]))
                        console.print("[green]Feito.[/green]")
                        
                        if conf.get('last_phone') == nome_removido:
                            conf['last_phone'] = None
                            salvar_config(conf)
                    except: pass
                    time.sleep(1)

def buscar_grupos():
    conf = carregar_config()
    api_id = conf['tg_api_id']
    api_hash = conf['tg_api_hash']
    
    sessao = obter_sessao_automatica()
    if not sessao: return

    client = TelegramClient(sessao, api_id, api_hash)

    async def buscar_grupos_async():
        try:
            await client.connect()
            if not await client.is_user_authorized():
                console.print("[red]Sessão inválida.[/red]"); return
            
            console.print("\n[green]Conectado! Carregando lista de grupos...[/green]")
            dialogs = []
            try:
                async for d in client.iter_dialogs(limit=None):
                    if d.is_group or d.is_channel: dialogs.append(d)
            except: pass
            
            banner()
            console.print("[bold cyan]--- BUSCAR GRUPOS POR NOME ---[/bold cyan]")
            termo = input_seguro("[cyan]Digite o nome do grupo ou V p/ Voltar: [/cyan]")
            if termo.lower() == 'v': return
            if not termo: return
            
            encontrados = []
            for d in dialogs:
                nome = getattr(d, 'name', '').lower()
                if termo.lower() in nome:
                    encontrados.append(d)
            
            if not encontrados:
                console.print(f"\n[red]Nenhum grupo encontrado com '{termo}'.[/red]")
                time.sleep(2)
                return
            
            banner()
            console.print(f"[green]Encontrados: {len(encontrados)} grupos[/green]")
            for i, d in enumerate(encontrados, 1):
                nome = getattr(d, 'name', 'Sem Nome')
                if len(nome) > 35: nome = nome[:32] + "..."
                console.print(f"[white][{i}] {nome}[/white]")
            
            console.print("\n[yellow][S] Salvar Lista em Arquivo[/yellow]")
            console.print("[green][E] Extrair Desta Busca (Scan)[/green]")
            console.print("[red][V] Voltar[/red]")
            op = input_seguro("\n[bold red]» Opção: [/bold red]", "V")
            
            if op.lower() == 's':
                nome_arquivo = input_seguro("[cyan]Nome do arquivo (sem .txt): [/cyan]")
                if nome_arquivo:
                    caminho = os.path.join(BASE_FOLDER, f"{nome_arquivo}.txt")
                    with open(caminho, 'w', encoding='utf-8') as f:
                        for d in encontrados:
                            nome = getattr(d, 'name', 'Sem Nome')
                            f.write(f"{nome}\n")
                    console.print(f"[green]Lista salva em: {caminho}[/green]")
                    time.sleep(2)
            
            elif op.lower() == 'e':
                banner()
                console.print("[bold cyan]--- SELEÇÃO PARA SCAN ---[/bold cyan]")
                
                for i, d in enumerate(encontrados, 1):
                    nome = getattr(d, 'name', 'Sem Nome')
                    if len(nome) > 35: nome = nome[:32] + "..."
                    console.print(f"[white][{i}] {nome}[/white]")

                console.print(f"\n[yellow][T] Escanear TODOS os {len(encontrados)} grupos listados[/yellow]")
                console.print("[white]Ou digite os números separados por vírgula (Ex: 1,3)[/white]")
                console.print("[red][V] Voltar[/red]")
                
                sel_scan = input_seguro("\n[bold red]» Escolha: [/bold red]", "T")
                if sel_scan.lower() == 'v': return
                
                alvos_scan = []
                if sel_scan.lower() == 't': 
                    alvos_scan = encontrados
                else:
                    try:
                        indices = [int(x.strip()) for x in sel_scan.split(',') if x.strip().isdigit()]
                        alvos_scan = [encontrados[i-1] for i in indices if 0 <= i-1 < len(encontrados)]
                    except: pass
                
                if alvos_scan:
                    await configurar_e_rodar_scan(client, alvos_scan)
                else:
                    console.print("[red]Nenhum grupo selecionado.[/red]")
                    time.sleep(1)

        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
        finally:
            await client.disconnect()

    client.loop.run_until_complete(buscar_grupos_async())

def run_scan():
    conf = carregar_config()
    api_id = conf['tg_api_id']
    api_hash = conf['tg_api_hash']
    
    sessao = obter_sessao_automatica()
    if not sessao: return

    client = TelegramClient(sessao, api_id, api_hash)
    
    async def wrapper():
        try:
            await client.connect()
            if not await client.is_user_authorized():
                console.print("[red]Sessão inválida. Verifique em Gerenciar Contas.[/red]")
                return
            await configurar_e_rodar_scan(client)
        except Exception as e:
            console.print(f"[red]Erro de conexão: {e}[/red]")
        finally:
            await client.disconnect()

    client.loop.run_until_complete(wrapper())

def run_scan_servidor_alvo():
    from telethon.tl.types import InputMessagesFilterDocument, InputMessagesFilterUrl
    import asyncio

    conf = carregar_config()
    api_id = conf['tg_api_id']
    api_hash = conf['tg_api_hash']
    
    sessao = obter_sessao_automatica()
    if not sessao: return

    client = TelegramClient(sessao, api_id, api_hash)

    dados = {'cmb': set(), 'm3u': set()}
    fingerprints = set()
    stats_total = {'cmb': 0, 'm3u': 0}
    
    rex_url = re.compile(r'http[s]?://\S+')
    rex_login = re.compile(r'username=([^&"\s]+)&password=([^&"\s]+)')
    rex_host = re.compile(r'(http[s]?://[^/]+)')

    CONCURRENCY_LIMIT = 23
    MAX_FILE_SIZE = 15 * 1024 * 1024

    def norm(u):
        u = u.strip().rstrip('/')
        if u.endswith(':8080'): return u[:-5]
        elif u.endswith(':80'): return u[:-3]
        return u

    monitor = KeyMonitor()

    async def core_logic():
        try:
            await client.connect()
            if not await client.is_user_authorized():
                console.print("[red]Sessão inválida.[/red]"); return
        except: console.print("[red]Erro conexão.[/red]"); return

        console.print("\n[green]Conectado![/green]")
        
        banner()
        console.print("[bold cyan]--- SERVIDOR ALVO ---[/bold cyan]")
        console.print("[red][V] Voltar ao Menu Principal[/red]")
        
        target_servers = []
        while True:
            server = input_seguro("[cyan]Digite o servidor (ex: http://servidor.com): [/cyan]")
            if server.lower() == 'v': return
            if server:
                server_norm = norm(server.strip())
                target_servers.append(server_norm)
                console.print(f"[green]Servidor adicionado: {server_norm}[/green]")
                
                outro = input_seguro("[cyan]Deseja adicionar outro servidor? (S/N): [/cyan]", "N").lower()
                if outro != 's': break
            else: break
        
        if not target_servers:
            console.print("\n[red]Nenhum servidor informado.[/red]")
            time.sleep(2)
            return
        
        console.print(f"\n[green]Servidores alvo: {len(target_servers)}[/green]")
        for i, srv in enumerate(target_servers, 1): console.print(f"[white][{i}] {srv}[/white]")
        time.sleep(1)

        banner()
        console.print("[green]Carregando grupos...[/green]")
        
        dialogs = []
        try:
            async for d in client.iter_dialogs(limit=None):
                if d.is_group or d.is_channel: dialogs.append(d)
        except: pass

        banner()
        console.print("[bold cyan]--- LISTA DE GRUPOS ---[/bold cyan]")
        for i, d in enumerate(dialogs):
            nome = getattr(d, 'name', 'Sem Nome')
            if len(nome) > 35: nome = nome[:32] + "..."
            console.print(f"[white][{i}] {nome}[/white]")

        console.print(f"\n[yellow][T] TODOS os {len(dialogs)} grupos[/yellow]")
        console.print("[red][V] Voltar ao Menu Principal[/red]")
        sel = input_seguro("\n[bold red]» Escolha (ex: 1,3 ou T): [/bold red]", "T")
        if sel.lower() == 'v': return

        alvos = []
        if sel.lower() == 't': alvos = dialogs
        else:
            try:
                indices = [int(x.strip()) for x in sel.split(',') if x.strip().isdigit()]
                alvos = [dialogs[i] for i in indices if 0 <= i < len(dialogs)]
            except: pass
        if not alvos: alvos = dialogs

        banner()
        console.print(f"[green]Grupos Alvo: {len(alvos)}[/green]")
        
        console.print("\n[bold cyan]--- NOME PERSONALIZADO ---[/bold cyan]")
        op_nome = input_seguro("[green]Deseja salvar com nome personalizado? (S/N) ou V p/ Voltar: [/green]", "N").lower()
        if op_nome == 'v': return

        nome_personalizado = None
        if op_nome == 's':
            nome_personalizado = input_seguro("[cyan]Digite o nome (sem .txt): [/cyan]").strip()
            if not nome_personalizado: nome_personalizado = None
        
        console.print("\n[bold cyan]--- O QUE DESEJA SALVAR? 💾 ---[/bold cyan]")
        console.print("[yellow][1] Apenas Links M3U[/yellow]")
        console.print("[red][2] Apenas Combos (User:Pass)[/red]")
        console.print("[white][3] Ambos (M3U e Combos)[/white]")
        console.print("[red][V] Voltar[/red]")
        opt = input_seguro("\n[bold red]» Opção: [/bold red]", "3")
        if opt.lower() == 'v': return

        sv_m3u = opt in ['1','3']; sv_cmb = opt in ['2','3']

        console.print("\n[bold cyan]--- PERÍODO DE BUSCA 🗓️ ---[/bold cyan]")
        console.print("[1] 7 Dias\n[2] 15 Dias\n[3] 30 Dias\n[4] 60 Dias\n[5] 90 Dias\n[6] 120 Dias\n[7] Tudo\n[8] Data Personalizada")
        console.print("[red][V] Voltar[/red]")
        d = input_seguro("\n[bold red]» Opção: [/bold red]", "3")
        if d.lower() == 'v': return
        
        date_range = None
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if d=='1': date_range = {'start': now - timedelta(days=7), 'end': now}
        elif d=='2': date_range = {'start': now - timedelta(days=15), 'end': now}
        elif d=='3': date_range = {'start': now - timedelta(days=30), 'end': now}
        elif d=='4': date_range = {'start': now - timedelta(days=60), 'end': now}
        elif d=='5': date_range = {'start': now - timedelta(days=90), 'end': now}
        elif d=='6': date_range = {'start': now - timedelta(days=120), 'end': now}
        elif d=='8':
            while True:
                try:
                    console.print("\n[bold cyan]--- DATA PERSONALIZADA ---[/bold cyan]")
                    console.print("[red][V] Voltar[/red]")
                    data_inicio_str = input_seguro("[cyan]Data inicial (dd/mm/aaaa): [/cyan]")
                    if data_inicio_str.lower() == 'v': return
                    data_fim_str = input_seguro("[cyan]Data final (dd/mm/aaaa): [/cyan]")
                    if data_fim_str.lower() == 'v': return

                    data_inicio = datetime.datetime.strptime(data_inicio_str, "%d/%m/%Y")
                    data_fim = datetime.datetime.strptime(data_fim_str, "%d/%m/%Y")
                    data_inicio = data_inicio.replace(tzinfo=timezone.utc)
                    data_fim = data_fim.replace(tzinfo=timezone.utc)
                    data_fim = data_fim.replace(hour=23, minute=59, second=59)
                    if data_inicio > data_fim:
                        console.print("[red]Data inicial não pode ser maior que data final![/red]")
                        continue
                    date_range = {'start': data_inicio, 'end': data_fim}
                    break
                except: console.print("[red]Formato inválido! Use dd/mm/aaaa[/red]")
        
        if not date_range: date_range = {'start': None, 'end': None}

        console.print("\n[bold cyan]--- MODO DE LEITURA 🔍 ---[/bold cyan]")
        console.print("[1] Ler apenas Mensagens de Texto\n[2] Baixar e Ler Arquivos (.txt)\n[3] Ambos (Completo)")
        console.print("[red][V] Voltar[/red]")
        mod = input_seguro("\n[bold red]» Opção: [/bold red]", "3")
        if mod.lower() == 'v': return
        do_txt = mod in ['1','3']; do_file = mod in ['2','3']

        stats = {'msg':0, 'txt':0, 'skip':0}
        start = time.time()
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

        def parse(text):
            found = False
            for link in rex_url.findall(text):
                if "username=" in link:
                    try:
                        creds = rex_login.search(link)
                        host = rex_host.search(link)
                        if creds and host:
                            u, p = creds.group(1), creds.group(2)
                            h_raw = host.group(1)
                            h_norm = norm(h_raw)
                            if h_norm not in target_servers: continue
                            
                            fp = f"{u}:{p}@{h_norm}"
                            if sv_cmb: stats_total['cmb'] += 1
                            if sv_m3u: stats_total['m3u'] += 1
                            
                            if fp not in fingerprints:
                                if sv_cmb: dados['cmb'].add(f"{u}:{p}")
                                if sv_m3u: dados['m3u'].add(f"{h_norm}/get.php?username={u}&password={p}&type=m3u_plus")
                                fingerprints.add(fp)
                                found = True
                    except: pass
            return found

        async def download_worker(msg):
            async with semaphore:
                try:
                    preview = b''
                    async for chunk in client.iter_download(msg.document, request_size=4096):
                        preview += chunk
                        if len(preview) >= 20480: break
                    decoded_preview = preview.decode('utf-8', 'ignore')
                    if 'username=' not in decoded_preview and 'http' not in decoded_preview: return
                    content = await msg.download_media(file=bytes)
                    if parse(content.decode('utf-8', 'ignore')): pass
                    stats['txt'] += 1
                except: pass

        def gerar_painel_progresso(grupo_atual, grupo_idx, total_grupos):
            elap = time.time() - start
            mins, secs = divmod(int(elap), 60)
            
            grid = Table.grid(expand=True, padding=(0, 1))
            grid.add_column(justify="left")
            grid.add_row(Align.center("[bold orange1 on black]>>> [S] PARA PARAR E SALVAR <<<[/]"))
            grid.add_row("")
            grid.add_row(f"[bold white]📂 Grupo Atual:[/]")
            nome_safe = grupo_atual[:30] + "..." if len(grupo_atual) > 35 else grupo_atual
            grid.add_row(f"[yellow]{nome_safe} ({grupo_idx}/{total_grupos})[/]")
            grid.add_row(f"[bold white]⏱️ Tempo Decorrido:[/][yellow] {mins:02}:{secs:02}[/]")
            grid.add_row("[dim]" + "─" * 25 + "[/]")
            grid.add_row(f"[white]📨 Mensagens Lidas:   [/][cyan]{stats['msg']:,}[/]")
            grid.add_row(f"[white]📄 Arquivos Baixados: [/][cyan]{stats['txt']:,}[/]")
            grid.add_row(f"[white]⏭️ Grupos Pulados:    [/][red]{stats['skip']}[/]")
            grid.add_row("[dim]" + "─" * 25 + "[/]")
            grid.add_row(f"[green]🟢 Links M3U:          {len(dados['m3u']):,}[/]")
            grid.add_row(f"[cyan]🔵 Combos Encontrados: {len(dados['cmb']):,}[/]")

            return Panel(
                grid, 
                style="green", 
                border_style="#EEE8AA", 
                title="[bold green]SCANNER TELEGRAM - SERVIDOR ALVO[/]",
                subtitle="[#696969]ʙʏ ᴍᴀʀʟᴏɴ[/#696969]"
            )

        banner()
        monitor.start()
        
        with Live(gerar_painel_progresso("Iniciando...", 0, len(alvos)), refresh_per_second=12, console=console) as live:
            for idx, grp in enumerate(alvos, 1):
                if monitor.key_pressed == 's': break
                nome_grp = getattr(grp, 'name', 'Grupo')
                
                tem_conteudo = False
                try:
                    if do_file:
                        res = await client.get_messages(grp, limit=1, filter=InputMessagesFilterDocument)
                        if res.total > 0: tem_conteudo = True
                    if not tem_conteudo and do_txt:
                        res = await client.get_messages(grp, limit=1, filter=InputMessagesFilterUrl)
                        if res.total > 0: tem_conteudo = True
                    
                    if not tem_conteudo:
                        stats['skip'] += 1
                        continue 
                except: pass

                streak = 0
                download_tasks = []

                try:
                    async for msg in client.iter_messages(grp):
                        if monitor.key_pressed == 's': break
                        if date_range['start'] and msg.date < date_range['start']: break
                        if date_range['end'] and msg.date > date_range['end']: continue
                        
                        stats['msg'] += 1
                        hit = False
                        
                        if do_txt and msg.text:
                            if parse(msg.text): hit = True
                        if do_file and msg.document:
                            is_valid = False
                            if hasattr(msg.document, 'attributes'):
                                for attr in msg.document.attributes:
                                    if isinstance(attr, DocumentAttributeFilename):
                                        if attr.file_name.lower().endswith(('.txt', '.m3u', '.cfg')):
                                            is_valid = True
                            if is_valid and msg.document.size < MAX_FILE_SIZE:
                                hit = True
                                download_tasks.append(download_worker(msg))
                        
                        if hit: streak = 0
                        else: streak += 1
                        
                        if len(download_tasks) >= 20:
                            await asyncio.gather(*download_tasks)
                            download_tasks = []
                            live.update(gerar_painel_progresso(nome_grp, idx, len(alvos)))

                        if streak >= 600:
                            stats['skip'] += 1
                            break
                        if stats['msg'] % 20 == 0:
                            live.update(gerar_painel_progresso(nome_grp, idx, len(alvos)))
                    if download_tasks: await asyncio.gather(*download_tasks)

                except: pass
                live.update(gerar_painel_progresso(nome_grp, idx, len(alvos)))
        
        return time.time() - start, stats, nome_personalizado

    try:
        res = client.loop.run_until_complete(core_logic())
        dur, st, nome_personalizado = res if res else (0, {}, None)
    except KeyboardInterrupt:
        dur, st, nome_personalizado = 0, {}, None
    finally:
        monitor.stop()
        try: client.disconnect()
        except: pass

    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    dirs = {'Cmb': 'Combos', 'M3u': 'M3u'}
    for k,v in dirs.items(): os.makedirs(os.path.join(BASE_FOLDER, v), exist_ok=True)
    
    total_seconds = int(dur)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    tempo_total_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    banner()
    tb_res = Table(title="RELATÓRIO FINAL", box=box.ROUNDED)
    tb_res.add_column("Métrica", style="cyan")
    tb_res.add_column("Valor", style="white")
    
    tb_res.add_row("Tempo Decorrido", tempo_total_str)
    tb_res.add_row("Mensagens Lidas", f"{st.get('msg',0):,}")
    tb_res.add_row("Arquivos TXT Baixados", f"{st.get('txt',0):,}")
    tb_res.add_row("Grupos Pulados", f"{st.get('skip',0)}")
    
    sc = 0
    if dados['cmb']:
        import random 
        dup = stats_total['cmb'] - len(dados['cmb'])
        if nome_personalizado:
            p = os.path.join(BASE_FOLDER, 'Combos', f"{nome_personalizado}.txt")
        else:
            p = os.path.join(BASE_FOLDER, 'Combos', f"Combo_{len(dados['cmb'])}_{ts}.txt")
        lista_randomica = list(dados['cmb'])
        random.shuffle(lista_randomica)
        with open(p, 'w') as f: f.write('\n'.join(lista_randomica))
        tb_res.add_row("Combos Salvos", f"[green]{len(dados['cmb']):,}[/green] (Dup -{dup:,})")
        sc+=1

    if dados['m3u']:
        dup = stats_total['m3u'] - len(dados['m3u'])
        if nome_personalizado:
            p = os.path.join(BASE_FOLDER, 'M3u', f"{nome_personalizado}.txt")
        else:
            p = os.path.join(BASE_FOLDER, 'M3u', f"M3u_{len(dados['m3u'])}_{ts}.txt")
        with open(p, 'w') as f: f.write('\n'.join(sorted(dados['m3u'])))
        tb_res.add_row("M3U Salvos", f"[green]{len(dados['m3u']):,}[/green] (Dup -{dup:,})")
        sc+=1

    console.print(tb_res)
    if sc == 0: console.print("\n[red]Nenhum dado novo encontrado para salvar.[/red]")
    else: console.print(f"\n[yellow]Arquivos salvos em: {BASE_FOLDER}[/yellow]")
    input_seguro("\n[bold yellow]Enter para voltar...[/bold yellow]")

def menu_changelog():
    while True:
        banner()
        
        texto_log = """
[bold orange1]1. SISTEMA MULTI-SESSÕES (ILIMITADO)[/bold orange1]
[white]• Implementada a capacidade de gerenciar múltiplas contas do Telegram simultaneamente.
• [bold cyan]Funcionalidade:[/bold cyan] Permite logar com várias contas e alternar entre elas facilmente.[/white]

[bold orange1]2. MELHORIA DE NAVEGAÇÃO (VOLTAR)[/bold orange1]
[white]• Agora todas as telas de seleção, inserção de dados e configurações possuem a opção [bold red][V] Voltar[/bold red].
• Isso evita que você fique preso em um menu caso mude de ideia ou selecione algo errado.[/white]

[bold orange1]3. SESSÃO AUTOMÁTICA[/bold orange1]
[white]• O script agora memoriza a última conta utilizada e entra nela automaticamente ao iniciar as funções de extração.
• Para trocar de conta, utilize o menu "Gerenciar Contas" e defina uma nova conta padrão.[/white]

[bold orange1]4. MODO TURBO (PERFORMANCE)[/bold orange1]
[white]• Adicionada opção de [bold red]Modo Turbo[/] nas configurações.
• Aumenta drasticamente a velocidade de download de arquivos.
• [bold red]ATENÇÃO:[/bold red] O uso abusivo pode causar FloodWait. Use com moderação.[/white]

[bold orange1]5. MOTOR DE SCAN E EXTRAÇÃO[/bold orange1]
[white]A função primária do script é a mineração de dados em grupos, operando em três frentes:
  • [bold magenta]Servidores (DNS):[/bold magenta] Extrai os servidores dos links m3u.
  • [bold red]Combos (User:Pass):[/bold red] Gera listas limpas focadas em [i]account checking[/i].
  • [bold green]Listas M3U:[/bold green] Captura links completos para reprodução direta.[/white]
"""
        console.print(Panel(
            texto_log.strip(),
            title="[bold white on deep_sky_blue1] CHANGELOG & FUNCIONALIDADES v1.0 [/]",
            border_style="deep_sky_blue1",
            padding=(1, 1)
        ))

        input_seguro("\n[bold yellow]Pressione Enter para voltar ao Menu Principal...[/bold yellow]")
        break

def main():
    restaurar_terminal()
    carregar_config()
    while True:
        banner()
        console.print("[bold cyan][ MENU PRINCIPAL ][/bold cyan]")
        console.print("[green][1] Iniciar Extração (Geral)[/green]")
        console.print("[blue][2] Extração Servidor Alvo[/blue]")
        console.print("[yellow][3] Buscar Grupos[/yellow]")
        console.print("[white][4] Gerenciar Contas[/white]")
        console.print("[magenta][5] Configurações API[/magenta]")
        console.print("[red][6] Configurações[/red]")
        console.print("[cyan][7] Tutorial / Ajuda[/cyan]")
        console.print("[orange1][8] Changelog[/orange1]")
        console.print("[red][0] Sair[/red]")
        
        op = input_seguro("\n[bold red]» Opção: [/bold red]", "0")
        
        if op == '1': run_scan()
        elif op == '2': run_scan_servidor_alvo()
        elif op == '3': buscar_grupos()
        elif op == '4': menu_sessoes()
        elif op == '5': menu_config_api()
        elif op == '6': menu_configuracoes()
        elif op == '7': menu_tutorial()
        elif op == '8': menu_changelog()
        elif op == '0': sys.exit()

if __name__ == "__main__":
    main()