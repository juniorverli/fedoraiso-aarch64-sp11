# Áudio no Fedora 44: evidência antes de alterar

Execute no Surface inicializado em Fedora, como usuário da sessão GNOME. O microfone foi relatado como funcional; preserve sua configuração. WSL e rootfs extraído não validam placa, canais ou DSP.

```sh
python3 scripts/collect-fedora-session.py --section audio
wpctl status
wpctl inspect @DEFAULT_AUDIO_SINK@
wpctl inspect @DEFAULT_AUDIO_SOURCE@
wpctl get-volume @DEFAULT_AUDIO_SINK@
pactl list cards
pactl list sinks
pactl list sources
aplay -l
arecord -l
alsaucm listcards
```

O coletor apenas lista dispositivos; `arecord -l` não grava. Revise `summary.txt`, os códigos/erros em `audio.json` e `manifest.json`. O diretório privado fica em `research/camera-sensors/raw/`, ignorado pelo Git; logs podem conter identificadores. Ferramenta ausente ou permissão negada significa lacuna de evidência, não ausência de hardware. Não execute o coletor com sudo.

Registre nome/índice ALSA, nome UCM, perfil ativo e perfis disponíveis da placa em `pactl list cards`; correlacione com `device.name`, `device.profile.name`, `api.alsa.card` e `audio.position` no `wpctl inspect`. Para inspecionar UCM, substitua `NOME_DA_PLACA` pelo identificador obtido (não adivinhe):

```sh
alsaucm -c NOME_DA_PLACA list _verbs
# Se HiFi aparecer na lista:
alsaucm -c NOME_DA_PLACA list _devices/HiFi
rpm -q alsa-ucm pipewire wireplumber
```

Compare os arquivos `/usr/share/alsa/ucm2/Qualcomm/x1e80100/` e o dispatcher com os arquivos fornecidos pelo pacote (`rpm -V alsa-ucm`). O builder mantém o UCM da distribuição quando disponível e adiciona o perfil Surface revisado quando necessário. Não importe ACDB/UCM de outra máquina nem ative controles de amplificador por tentativa.

Verifique `Channel Map` em `pactl list sinks` e `audio.position` no nó: espere FL/FR quando a saída selecionada for estéreo. Uma declaração FL/FR só confirma o mapa lógico. Para confirmar esquerda/direita fisicamente, use o teste de canais de Configurações → Som somente após confirmar a condição segura da proteção e mantendo o limite existente; documente qual lado responde. Não use sinais de teste contínuos nos alto-falantes ainda sem proteção validada.

## Proteção dos alto-falantes

A proteção exige caminho DSP/AudioReach, realimentação de tensão/corrente (VI), controles do amplificador e calibração específicos. Consulte [a investigação de proteção](rea/SPEAKER_PROTECTION_FINDINGS.md). Existe implementação externa para X1E; sua adaptação e validação no nosso X1P continuam pendentes. Uma afirmação anterior sobre ausência em todos os X1E não deve ser tomada como conclusão atual.

Mantenha os limites de ganho atuais. EQ, AEC, redução de ruído, taxa de amostragem e o preset legado `configs/pipewire/pipewire.conf.d/10-surface-sp11-audio.conf` não fornecem essa proteção. O builder não instala esse preset; seu comentário sobre proteção/beamforming não comprova implementação. Não o copie para a sessão.

## Taxa, quantum e falhas

```sh
pw-top
pw-metadata -n settings
journalctl --user -b -n 150 --no-pager -u pipewire -u pipewire-pulse -u wireplumber
```

Em `pw-top`, observe RATE, QUANT e o aumento de ERR durante a mesma carga de trabalho. Anote valores antes/depois e erros de underrun/XRUN no journal. Quantum maior pode reduzir falhas ao custo de latência; aumentar a taxa não cria fidelidade ausente na fonte ou no hardware. O quantum efetivo pode ser solicitado pelo aplicativo e diferir do padrão.

Compare primeiro com o padrão Fedora. Liste overrides em `~/.config/pipewire`, `~/.config/wireplumber`, `/etc/pipewire` e `/etc/wireplumber`; não apague arquivos do pacote em `/usr/share`. Faça cópia privada dos diretórios de usuário existentes antes de movê-los temporariamente para um backup. Registre também quaisquer mudanças de sistema para reversão pelo administrador.

Somente se a medição demonstrar XRUNs e justificar maior buffer, este exemplo altera o padrão do usuário (não proteção). Execute os blocos de alteração conscientemente; feche chamadas, gravações e players, pois reiniciar interrompe áudio:

```sh
audio_example_created=false
audio_backup="$HOME/.local/state/surface-audio-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 -p "$audio_backup" || exit 1
[ ! -d "$HOME/.config/pipewire" ] || cp -a "$HOME/.config/pipewire" "$audio_backup/" || exit 1
mkdir -p "$HOME/.config/pipewire/pipewire.conf.d" || exit 1
# Recusa sobrescrever um ajuste existente.
(set -C; cat > "$HOME/.config/pipewire/pipewire.conf.d/90-surface-measured.conf" <<'EOF'
context.properties = {
    default.clock.quantum = 1024
}
EOF
) || exit 1
audio_example_created=true
systemctl --user restart pipewire.service pipewire-pulse.service wireplumber.service || exit 1
```

Meça novamente. Execute o rollback na mesma sessão de shell; se a criação recusou um arquivo existente, pare e preserve esse arquivo. A variável só autoriza remoção quando esta execução criou o exemplo com sucesso:

```sh
[ "${audio_example_created:-false}" = true ] || { echo 'Exemplo não criado nesta sessão; pare sem remover arquivos.' >&2; exit 1; }
rm -- "$HOME/.config/pipewire/pipewire.conf.d/90-surface-measured.conf" || exit 1
audio_example_created=false
systemctl --user restart pipewire.service pipewire-pulse.service wireplumber.service || exit 1
```

Restaure separadamente overrides movidos durante comparação; não restaure toda a árvore por cima de mudanças posteriores.

Fontes primárias consultadas em 2026-10-15: [pw-top](https://docs.pipewire.org/page_man_pw-top_1.html), [configuração PipeWire](https://docs.pipewire.org/page_man_pipewire_conf_5.html), [locais WirePlumber](https://pipewire.pages.freedesktop.org/wireplumber/daemon/locations.html), [ALSA alsaucm](https://github.com/alsa-project/alsa-utils/blob/master/alsaucm/alsaucm.rst). Confirme versões instaladas antes de adaptar instruções.
