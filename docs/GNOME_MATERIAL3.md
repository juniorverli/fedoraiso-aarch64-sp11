# GNOME 50, Wayland e aparência inspirada em Material 3

O Fedora 44 fornece GNOME 50 ([pacote oficial](https://packages.fedoraproject.org/pkgs/gnome-shell/gnome-shell/fedora-44.html)). Confirme a instalação física; um rootfs ou sessão WSL não demonstra o protocolo de uma aplicação no Surface.

## Confirmar sessão e cada aplicativo

```sh
python3 scripts/collect-fedora-session.py --section desktop
gnome-shell --version
printf '%s\n' "$XDG_SESSION_TYPE" "$XDG_CURRENT_DESKTOP" "$WAYLAND_DISPLAY" "$DISPLAY"
[ -z "$XDG_SESSION_ID" ] || loginctl show-session "$XDG_SESSION_ID" -p Type -p Desktop -p State
pgrep -x Xwayland
xlsclients -l
```

`Type=wayland` confirma a sessão. `DISPLAY` pode existir para compatibilidade. Um processo Xwayland ativo não prova que determinado aplicativo usa X11; `pgrep` retorna 1 sem correspondências. `xlsclients` pode identificar clientes X11 no display acessível, mas saída vazia não cobre todos os processos, displays ou instâncias.

Feche a instância anterior antes de testar, para evitar que um lançamento apenas encaminhe a solicitação ao processo antigo. Em aplicativo GTK, lance `GTK_DEBUG=interactive nome-do-aplicativo`, se o Inspector estiver habilitado, e examine o display/backend em suas informações gerais. Como teste estrito por aplicativo, `GDK_BACKEND=wayland nome-do-aplicativo` exige backend Wayland; registre sucesso e eventuais falhas. [GTK documenta o Inspector e suas limitações](https://docs.gtk.org/gtk4/running.html) e o [backend Wayland](https://docs.gtk.org/gtk4/wayland).

No Firefox, abra `about:support` e registre **Window Protocol/Protocolo de janelas** da instância testada: `wayland` confirma seu protocolo. No Chromium, use uma instância separada:

```sh
chromium --user-data-dir="$HOME/.cache/chromium-wayland-test" --ozone-platform=wayland
```

Confirme o comando em `chrome://version` e informações Ozone/Wayland em `chrome://gpu`, se expostas pela compilação. O sinalizador é uma solicitação; combine-o com evidência da instância. O diretório de teste contém um perfil separado; não use ali contas ou dados privados. A implementação Ozone é descrita pelo [projeto Chromium](https://chromium.googlesource.com/chromium/src/+/main/docs/ozone_overview.md).

Para uma aplicação Qt compatível: `QT_QPA_PLATFORM=wayland nome-do-aplicativo`; o plugin Qt Wayland deve estar instalado. Não exporte essas variáveis globalmente como certificado de conformidade: elas não convertem aplicativos exclusivos de X11.

Para diagnóstico adicional de um alvo, sem sessão inteira:

```sh
umask 077
WAYLAND_DEBUG=client nome-do-aplicativo 2> "$HOME/wayland-alvo.log"
```

Tráfego de protocolo emitido pelo alvo é evidência adicional; ausência pode resultar de processo já aberto, toolkit ou subprocesso diferente. Logs podem expor títulos/ações: revise antes de compartilhar e remova quando terminar. Repita o inventário por aplicativo, versão e janela. Wayland estrito exige substituir aplicações X11 restantes; não se resolve apenas por variáveis de ambiente.

## Primeiro: opções nativas e rollback

Faça backup no próprio Fedora antes das mudanças:

```sh
visual_backup="$HOME/.local/state/surface-visual-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 -p "$visual_backup"
dconf dump /org/gnome/desktop/interface/ > "$visual_backup/interface.dconf"
dconf dump /org/gnome/desktop/background/ > "$visual_backup/background.dconf"
for visual_dir in gtk-3.0 gtk-4.0 matugen; do
    [ ! -d "$HOME/.config/$visual_dir" ] || cp -a "$HOME/.config/$visual_dir" "$visual_backup/"
done
```

Em Configurações → Aparência, escolha fundo local e modo claro/escuro; escolha a cor de destaque mais próxima da paleta desejada. Por terminal, estas opções nativas são explícitas:

```sh
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
# Confira fontes instaladas antes de escolher outra:
fc-match Sans
gsettings set org.gnome.desktop.interface font-name 'Sans 11'
```

Para ícones, use o pacote Fedora disponível e revise a transação antes de confirmar:

```sh
dnf info papirus-icon-theme
sudo dnf install papirus-icon-theme
test -f /usr/share/icons/Papirus-Dark/index.theme && gsettings set org.gnome.desktop.interface icon-theme 'Papirus-Dark'
```

O [projeto Papirus](https://github.com/PapirusDevelopmentTeam/papirus-icon-theme) documenta requisitos de herança e instalação. Ícones simbólicos e ícones embutidos de apps podem permanecer próprios; confirme visualmente no Nautilus, painel e aplicativos. Registre versão com `rpm -q papirus-icon-theme`; não rode instalador remoto por curl.

## Paleta dinâmica revisável, sem extensão incompatível

Na consulta de 2026-10-15, [Material You 5236](https://extensions.gnome.org/extension/5236/material-you-color-theming/) declara Shell 42–44 e [Open Bar 6580](https://extensions.gnome.org/extension/6580/open-bar/) até 49. Nenhuma declara 50. Não desative a checagem de compatibilidade nem instale à força. Cores inspiradas em Material 3 não transformam layout, navegação e componentes de todos os apps em Material 3.

Uma rota independente de extensão é gerar cores a partir de imagem com Matugen e aplicar somente ajustes revisados. A referência auditada é [Matugen 4.2.0, revisão 9f8c7fd583e44310a642772ff8f13b693949baf2](https://github.com/InioX/matugen/tree/9f8c7fd583e44310a642772ff8f13b693949baf2). Requer Git, Rust/Cargo compatíveis com workspace resolver 3 (Rust/Cargo 1.84 ou posterior; dependências podem exigir versão mais recente), compilador/linker, acesso ao registro Cargo e espaço de construção. Confirme as versões e revise código, `Cargo.toml`, `Cargo.lock`, scripts de build e dependências antes de compilar. Comandos abaixo baixam e instalam explicitamente em diretório dedicado do usuário:

```sh
mkdir -p "$HOME/.local/src"
git clone https://github.com/InioX/matugen.git "$HOME/.local/src/surface-matugen"
git -C "$HOME/.local/src/surface-matugen" checkout --detach 9f8c7fd583e44310a642772ff8f13b693949baf2
git -C "$HOME/.local/src/surface-matugen" rev-parse HEAD
# Após revisar a árvore e o lockfile:
cargo install --locked --path "$HOME/.local/src/surface-matugen" --root "$HOME/.local/opt/surface-matugen"
"$HOME/.local/opt/surface-matugen/bin/matugen" --help
```

A árvore dedicada deve ser nova; crie `~/.local/src` previamente se necessário. Não reutilize checkout com alterações. A instalação e o template abaixo não foram executados no Fedora físico; qualquer falha de compilação deve ser registrada sem relaxar o lockfile.

Gere primeiro uma amostra em diretório isolado. Escolha uma imagem local legível (substitua o caminho absoluto do exemplo). O template gera apenas três cores para revisão:

```sh
palette_work="$HOME/.local/state/surface-palette"
mkdir -p "$HOME/.local/state" || exit 1
# mkdir exclusivo recusa diretório existente, incluindo symlink.
mkdir -m 700 "$palette_work" || { echo "Destino já existe ou não pôde ser criado; pare sem sobrescrever." >&2; exit 1; }
cat > "$palette_work/accent.template.css" <<'EOF'
@define-color accent_color {{colors.primary.default.hex}};
@define-color accent_bg_color {{colors.primary.default.hex}};
@define-color accent_fg_color {{colors.on_primary.default.hex}};
EOF
cat > "$palette_work/config.toml" <<'EOF'
[config]
version_check = false
[config.wallpaper]
set = false
[templates.accent]
input_path = "./accent.template.css"
output_path = "./accent.generated.css"
EOF
"$HOME/.local/opt/surface-matugen/bin/matugen" -c "$palette_work/config.toml" -m dark --source-color-index 0 image /caminho/absoluto/fundo.jpg
cat "$palette_work/accent.generated.css"
```

Para uma nova imagem, repita a geração; selecione em Configurações a cor nativa mais próxima. Essa rota funciona sem modificar Shell. O arquivo é um ponto de partida para ajustes GTK experimentais: após backup, copie-o como `~/.config/gtk-3.0/surface-accent.css` ou `~/.config/gtk-4.0/surface-accent.css` e acrescente **uma vez**, no início do respectivo `gtk.css`, `@import url("surface-accent.css");`. Preserve o restante do CSS. Reabra apenas um aplicativo e avalie contraste, foco, botões e modo claro antes de ampliar. Variáveis modernas libadwaita podem exigir CSS diferente; não prometa que esses três nomes alteram todos os componentes.

GTK3 e GTK4 possuem CSS/APIs diferentes. Libadwaita integra cor/modo nativos, mas substituição arbitrária de tema/CSS pode quebrar aparência entre versões. Shell não lê o `gtk.css` dos aplicativos. Flatpaks usam runtime e sandbox próprios: não conceda acesso amplo ao HOME para impor tema; prefira preferências nativas do app e seus overrides específicos após verificar permissões. Qt, Electron e páginas web exigem integração própria. A geração manual é dinâmica em relação à imagem escolhida; atualização automática em todos os apps e Shell 50 permanece trabalho separado, sem extensão compatível validada.

Para rollback, remova as linhas `@import` adicionadas e os dois `surface-accent.css`, restaurando os arquivos originais do backup quando necessário; feche/reabra os apps. Restaure escolhas nativas com `dconf load /org/gnome/desktop/interface/ < "$visual_backup/interface.dconf"` e `dconf load /org/gnome/desktop/background/ < "$visual_backup/background.dconf"`. Isso restaura as chaves exportadas; chaves ausentes devem ser revertidas individualmente com `gsettings reset` se foram criadas no teste. Remova os diretórios dedicados Matugen apenas após confirmar que não contêm outros dados. Registre resultados com capturas manuais sem informações privadas.
