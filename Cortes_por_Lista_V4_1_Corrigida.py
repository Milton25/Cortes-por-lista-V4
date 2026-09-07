# -*- coding: utf-8 -*-
"""
CORTES POR LISTA - V4.1 CORRIGIDA
DaVinci Resolve - Windows

Correção principal desta versão:
- O playhead é posicionado pela API do Resolve.
- Antes de enviar Ctrl+B, o script força o DaVinci Resolve para primeiro plano.
- O atalho é enviado diretamente pelo Windows.
- O foco volta para o Resolve a cada corte.

Formato aceito:
HH:MM:SS:FF
"""

import os
import sys
import time
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox

# ============================================================
# CONEXÃO COM DAVINCI RESOLVE
# ============================================================

def carregar_resolve():
    caminhos = [
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules",
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules",
    ]

    for caminho in caminhos:
        if os.path.isdir(caminho) and caminho not in sys.path:
            sys.path.append(caminho)

    try:
        import DaVinciResolveScript as dvr_script
        return dvr_script
    except Exception as e:
        raise RuntimeError(
            "Não foi possível carregar o módulo DaVinciResolveScript.\n\n"
            f"Erro: {e}"
        )


def conectar_resolve():
    dvr_script = carregar_resolve()
    resolve = dvr_script.scriptapp("Resolve")

    if not resolve:
        raise RuntimeError("Não foi possível conectar ao DaVinci Resolve.")

    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject() if project_manager else None

    if not project:
        raise RuntimeError("Nenhum projeto aberto no DaVinci Resolve.")

    timeline = project.GetCurrentTimeline()

    if not timeline:
        raise RuntimeError("Nenhuma timeline ativa no DaVinci Resolve.")

    return resolve, project, timeline


# ============================================================
# CONTROLE DE FOCO DO WINDOWS
# ============================================================

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_RESTORE = 9
VK_CONTROL = 0x11
VK_B = 0x42
KEYEVENTF_KEYUP = 0x0002


def encontrar_janela_resolve():
    """Procura a janela principal do DaVinci Resolve."""
    resultado = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            tamanho = user32.GetWindowTextLengthW(hwnd)
            if tamanho > 0:
                buffer = ctypes.create_unicode_buffer(tamanho + 1)
                user32.GetWindowTextW(hwnd, buffer, tamanho + 1)
                titulo = buffer.value.lower()

                if "davinci resolve" in titulo:
                    resultado.append(hwnd)

        return True

    user32.EnumWindows(enum_callback, 0)

    return resultado[0] if resultado else None


def ativar_resolve():
    """
    Força a janela do DaVinci Resolve para o primeiro plano.
    """
    hwnd = encontrar_janela_resolve()

    if not hwnd:
        return False

    try:
        user32.ShowWindow(hwnd, SW_RESTORE)

        # Técnica para aumentar a chance de SetForegroundWindow funcionar.
        foreground = user32.GetForegroundWindow()
        current_thread = kernel32.GetCurrentThreadId()
        foreground_thread = user32.GetWindowThreadProcessId(
            foreground, None
        )

        if foreground_thread:
            user32.AttachThreadInput(
                current_thread,
                foreground_thread,
                True
            )

        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.SetActiveWindow(hwnd)
        user32.SetFocus(hwnd)

        if foreground_thread:
            user32.AttachThreadInput(
                current_thread,
                foreground_thread,
                False
            )

        return True

    except Exception:
        try:
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False


def enviar_ctrl_b():
    """
    Envia Ctrl+B diretamente pelo Windows.
    Esse é o comando de corte testado no DaVinci Resolve.
    """

    # Pressiona CTRL
    user32.keybd_event(VK_CONTROL, 0, 0, 0)

    # Pressiona B
    user32.keybd_event(VK_B, 0, 0, 0)

    # Solta B
    user32.keybd_event(VK_B, 0, KEYEVENTF_KEYUP, 0)

    # Solta CTRL
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


# ============================================================
# TIME CODES
# ============================================================

def normalizar_timecode(valor):
    valor = valor.strip()

    if not valor:
        return None

    # Permite ponto ou vírgula como separador em casos de cópia.
    valor = valor.replace(";", ":")

    partes = valor.split(":")

    if len(partes) != 4:
        raise ValueError(
            f"Timecode inválido: {valor}\n"
            "Use o formato HH:MM:SS:FF"
        )

    try:
        h, m, s, f = [int(x) for x in partes]
    except ValueError:
        raise ValueError(
            f"Timecode inválido: {valor}\n"
            "Use somente números."
        )

    if h < 0 or m < 0 or s < 0 or f < 0:
        raise ValueError(f"Timecode inválido: {valor}")

    if m >= 60 or s >= 60:
        raise ValueError(
            f"Timecode inválido: {valor}\n"
            "Minutos e segundos devem ser menores que 60."
        )

    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def obter_lista_timecodes(texto, ordenar=False, remover_duplicados=True):
    lista = []

    for linha in texto.splitlines():
        linha = linha.strip()

        if not linha:
            continue

        tc = normalizar_timecode(linha)

        if tc:
            lista.append(tc)

    if remover_duplicados:
        nova_lista = []
        vistos = set()

        for tc in lista:
            if tc not in vistos:
                nova_lista.append(tc)
                vistos.add(tc)

        lista = nova_lista

    if ordenar:
        lista.sort(
            key=lambda tc: tuple(
                int(x) for x in tc.split(":")
            )
        )

    return lista


# ============================================================
# APLICAÇÃO
# ============================================================

class CortesPorListaV41:

    def __init__(self, root):
        self.root = root

        self.root.title("Cortes por Lista - V4.1 Corrigida")
        self.root.geometry("570x690")
        self.root.resizable(True, True)

        self.executando = False
        self.parar = False

        self.criar_interface()

    # --------------------------------------------------------

    def criar_interface(self):

        titulo = tk.Label(
            self.root,
            text="CORTES POR LISTA - V4.1",
            font=("Arial", 17, "bold")
        )
        titulo.pack(pady=(18, 4))

        subtitulo = tk.Label(
            self.root,
            text=(
                "Cole um timecode por linha.\n"
                "Formato aceito: HH:MM:SS:FF"
            ),
            font=("Arial", 9)
        )
        subtitulo.pack(pady=(0, 12))

        frame_lista = tk.LabelFrame(
            self.root,
            text="Lista de timecodes",
            padx=8,
            pady=8
        )
        frame_lista.pack(
            fill="both",
            expand=True,
            padx=14,
            pady=4
        )

        self.texto = tk.Text(
            frame_lista,
            font=("Consolas", 11),
            height=18
        )

        self.texto.pack(
            fill="both",
            expand=True
        )

        frame_botoes = tk.Frame(self.root)
        frame_botoes.pack(pady=8)

        tk.Button(
            frame_botoes,
            text="IMPORTAR .TXT",
            command=self.importar_txt
        ).grid(row=0, column=0, padx=4)

        tk.Button(
            frame_botoes,
            text="SALVAR LISTA .TXT",
            command=self.salvar_txt
        ).grid(row=0, column=1, padx=4)

        tk.Button(
            frame_botoes,
            text="LIMPAR",
            command=self.limpar
        ).grid(row=0, column=2, padx=4)

        frame_opcoes = tk.LabelFrame(
            self.root,
            text="Opções",
            padx=8,
            pady=8
        )
        frame_opcoes.pack(
            fill="x",
            padx=14,
            pady=5
        )

        self.var_ordenar = tk.BooleanVar(value=False)
        self.var_duplicados = tk.BooleanVar(value=True)
        self.var_somente_posicionar = tk.BooleanVar(value=False)

        tk.Checkbutton(
            frame_opcoes,
            text="Ordenar timecodes antes de executar",
            variable=self.var_ordenar
        ).pack(anchor="w")

        tk.Checkbutton(
            frame_opcoes,
            text="Remover timecodes duplicados",
            variable=self.var_duplicados
        ).pack(anchor="w")

        tk.Checkbutton(
            frame_opcoes,
            text="Somente posicionar o playhead (não cortar)",
            variable=self.var_somente_posicionar
        ).pack(anchor="w")

        frame_config = tk.LabelFrame(
            self.root,
            text="Configuração",
            padx=8,
            pady=8
        )
        frame_config.pack(
            fill="x",
            padx=14,
            pady=5
        )

        tk.Label(
            frame_config,
            text="Pausa após mover (segundos):"
        ).grid(row=0, column=0, sticky="w")

        self.pausa_mover = tk.Entry(
            frame_config,
            width=10
        )
        self.pausa_mover.insert(0, "0.40")
        self.pausa_mover.grid(
            row=0,
            column=1,
            padx=8
        )

        tk.Label(
            frame_config,
            text="Pausa após cortar (segundos):"
        ).grid(row=1, column=0, sticky="w")

        self.pausa_corte = tk.Entry(
            frame_config,
            width=10
        )
        self.pausa_corte.insert(0, "0.25")
        self.pausa_corte.grid(
            row=1,
            column=1,
            padx=8
        )

        self.status = tk.Label(
            self.root,
            text="Aguardando execução.",
            anchor="w"
        )
        self.status.pack(
            fill="x",
            padx=16,
            pady=(8, 2)
        )

        self.progresso = tk.DoubleVar(value=0)

        self.barra = tk.Scale(
            self.root,
            variable=self.progresso,
            from_=0,
            to=100,
            orient="horizontal",
            showvalue=False,
            state="disabled"
        )

        self.barra.pack(
            fill="x",
            padx=14,
            pady=3
        )

        frame_execucao = tk.Frame(self.root)
        frame_execucao.pack(
            pady=10
        )

        self.botao_executar = tk.Button(
            frame_execucao,
            text="EXECUTAR TODOS OS CORTES",
            font=("Arial", 10, "bold"),
            command=self.executar
        )

        self.botao_executar.grid(
            row=0,
            column=0,
            padx=4
        )

        tk.Button(
            frame_execucao,
            text="TESTAR PRIMEIRO TIMECODE",
            command=self.testar_primeiro
        ).grid(
            row=0,
            column=1,
            padx=4
        )

        tk.Button(
            frame_execucao,
            text="PARAR",
            command=self.solicitar_parada
        ).grid(
            row=0,
            column=2,
            padx=4
        )

        dica = tk.Label(
            self.root,
            text=(
                "Correção V4.1: o Resolve recebe foco novamente "
                "antes de cada Ctrl+B."
            ),
            font=("Arial", 8)
        )
        dica.pack(
            pady=(0, 8)
        )

    # --------------------------------------------------------

    def importar_txt(self):
        arquivo = filedialog.askopenfilename(
            title="Importar lista de timecodes",
            filetypes=[
                ("Arquivo TXT", "*.txt"),
                ("Todos os arquivos", "*.*")
            ]
        )

        if not arquivo:
            return

        try:
            with open(
                arquivo,
                "r",
                encoding="utf-8"
            ) as f:
                conteudo = f.read()

            self.texto.delete("1.0", tk.END)
            self.texto.insert(
                "1.0",
                conteudo
            )

        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Não foi possível importar o arquivo.\n\n{e}"
            )

    # --------------------------------------------------------

    def salvar_txt(self):
        arquivo = filedialog.asksaveasfilename(
            title="Salvar lista de timecodes",
            defaultextension=".txt",
            filetypes=[
                ("Arquivo TXT", "*.txt")
            ]
        )

        if not arquivo:
            return

        try:
            conteudo = self.texto.get(
                "1.0",
                tk.END
            )

            with open(
                arquivo,
                "w",
                encoding="utf-8"
            ) as f:
                f.write(conteudo)

        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Não foi possível salvar.\n\n{e}"
            )

    # --------------------------------------------------------

    def limpar(self):
        self.texto.delete(
            "1.0",
            tk.END
        )

    # --------------------------------------------------------

    def obter_pausas(self):
        try:
            mover = float(
                self.pausa_mover.get()
            )

            cortar = float(
                self.pausa_corte.get()
            )

            if mover < 0 or cortar < 0:
                raise ValueError

            return mover, cortar

        except ValueError:
            raise ValueError(
                "As pausas precisam ser números positivos."
            )

    # --------------------------------------------------------

    def executar_corte(self, timeline, tc, pausa_mover, pausa_corte):

        # 1. Posiciona o playhead pela API.
        resultado = timeline.SetCurrentTimecode(tc)

        if resultado is False:
            raise RuntimeError(
                f"Não foi possível posicionar o playhead em {tc}."
            )

        # Dá tempo para o Resolve atualizar visualmente.
        self.root.update()
        time.sleep(pausa_mover)

        # 2. ATIVA O DAVINCI RESOLVE.
        ativado = ativar_resolve()

        if not ativado:
            raise RuntimeError(
                "Não foi possível colocar o DaVinci Resolve em primeiro plano."
            )

        time.sleep(0.15)

        # 3. Envia CTRL+B.
        enviar_ctrl_b()

        time.sleep(pausa_corte)

    # --------------------------------------------------------

    def executar_lista(self, lista):

        self.executando = True
        self.parar = False

        try:
            resolve, project, timeline = conectar_resolve()

            pausa_mover, pausa_corte = (
                self.obter_pausas()
            )

            total = len(lista)
            realizados = 0

            for indice, tc in enumerate(lista, start=1):

                if self.parar:
                    self.status.config(
                        text=(
                            f"Processo interrompido. "
                            f"Cortes realizados: {realizados}/{total}"
                        )
                    )
                    break

                self.status.config(
                    text=(
                        f"Processando {indice}/{total}: {tc}"
                    )
                )

                self.progresso.set(
                    ((indice - 1) / total) * 100
                )

                self.root.update()

                if self.var_somente_posicionar.get():

                    resultado = timeline.SetCurrentTimecode(tc)

                    if resultado is False:
                        raise RuntimeError(
                            f"Não foi possível posicionar em {tc}."
                        )

                    time.sleep(pausa_mover)

                else:
                    self.executar_corte(
                        timeline,
                        tc,
                        pausa_mover,
                        pausa_corte
                    )

                realizados += 1

                self.progresso.set(
                    (indice / total) * 100
                )

                self.root.update()

            if not self.parar:
                self.status.config(
                    text=(
                        f"Processo finalizado. "
                        f"Total de cortes realizados: {realizados}"
                    )
                )

                messagebox.showinfo(
                    "Processo finalizado",
                    (
                        f"Total de cortes realizados: "
                        f"{realizados}"
                    )
                )

        except Exception as e:
            self.status.config(
                text="Erro durante a execução."
            )

            messagebox.showerror(
                "Erro",
                str(e)
            )

        finally:
            self.executando = False
            self.botao_executar.config(
                state="normal"
            )

    # --------------------------------------------------------

    def executar(self):

        if self.executando:
            return

        try:
            texto = self.texto.get(
                "1.0",
                tk.END
            )

            lista = obter_lista_timecodes(
                texto,
                ordenar=self.var_ordenar.get(),
                remover_duplicados=self.var_duplicados.get()
            )

            if not lista:
                messagebox.showwarning(
                    "Lista vazia",
                    "Digite pelo menos um timecode."
                )
                return

        except Exception as e:
            messagebox.showerror(
                "Timecode inválido",
                str(e)
            )
            return

        self.botao_executar.config(
            state="disabled"
        )

        # Executa no próprio loop para manter compatibilidade
        # com o ambiente de scripts do Resolve.
        self.executar_lista(lista)

    # --------------------------------------------------------

    def testar_primeiro(self):

        try:
            texto = self.texto.get(
                "1.0",
                tk.END
            )

            lista = obter_lista_timecodes(
                texto,
                ordenar=False,
                remover_duplicados=False
            )

            if not lista:
                messagebox.showwarning(
                    "Lista vazia",
                    "Digite pelo menos um timecode."
                )
                return

            resolve, project, timeline = conectar_resolve()

            pausa_mover, pausa_corte = (
                self.obter_pausas()
            )

            tc = lista[0]

            self.status.config(
                text=f"Testando: {tc}"
            )

            self.root.update()

            if self.var_somente_posicionar.get():

                timeline.SetCurrentTimecode(tc)

            else:

                self.executar_corte(
                    timeline,
                    tc,
                    pausa_mover,
                    pausa_corte
                )

            self.status.config(
                text=f"Teste concluído: {tc}"
            )

        except Exception as e:
            messagebox.showerror(
                "Erro no teste",
                str(e)
            )

    # --------------------------------------------------------

    def solicitar_parada(self):
        self.parar = True
        self.status.config(
            text="Solicitação de parada recebida..."
        )


# ============================================================
# INÍCIO
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = CortesPorListaV41(root)

    root.mainloop()
