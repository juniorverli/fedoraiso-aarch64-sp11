# Câmeras frontal e traseira: candidato para teste no Fedora

Estado: engenharia reversa e compilação avançaram; **funcionamento físico ainda não demonstrado nesta unidade**. A entrega final exige capturas da frontal e traseira, saída processada em aplicativo e análise dos erros/lifecycle. Este candidato não transforma testes de container em teste de hardware.

## O que foi preparado

- REA sobre os pacotes Windows desta máquina: inventário completo de 142 arquivos e recuperação das funções locais identificadas pelo Ghidra nos drivers frontal, traseiro, CSI, ISP e plataforma. Há 1151 funções / 88627 linhas de pseudocódigo retidas privadamente. A recuperação não equivale à compreensão ou prova de execução de todo o código.
- Decoder dos módulos Chromatix com CRC, limites e offsets verificáveis. As tabelas frontais de 364 + 68 registros coincidem exatamente com o candidato; a traseira tem uma diferença identificada em 207 registros. [Evidências e limitações](CAMERA_WINDOWS_MODULE_FINDINGS.md).
- Kernel diagnóstico `7.2.0-sp11-camera-x1p1`: Image, todos os 3767 módulos, DTB LCD e configuração. Todos os módulos têm o mesmo vermagic. A compilação em Fedora44/GCC16.2.1 terminou com exit 0; há dez avisos de tamanho de stack frame em código base, nenhum nos drivers de sensor/CAMSS. O DTB compilado confirmou resets frontal237/traseiro110, clock19.2MHz, C-PHY frontal e GPIO4 de backlight do LCD.
- Endpoint traseiro corrigido para também anunciar 592800000 Hz, frequência já usada no modo específico do driver. O patch reaplicou com fuzz=0 e gerou fonte idêntica. Não foi demonstrado que essa inconsistência fosse a causa da falha física.
- libcamera0.7.0 com os três patches IMX681: propriedades/atrasos, helper de ganho e tuning inicial. Inclui `cam`, Simple IPA/SoftISP, pipeline UVC, compatibilidade V4L2, udev e plugin GStreamer. Os caminhos de tuning/proxy/módulo IPA são selecionados pelo launcher. A compilação é nativa Fedora44 AArch64; teste de carregamento confirmou `libcamerasrc` do candidato e resolução de suas bibliotecas no container.

Artefatos locais:

| Arquivo | Conteúdo |
|---|---|
| `output/surface-camera-userspace-f44-aarch64.tar.gz` | Prefixo isolado `opt/surface-camera`, launcher `usr/local/bin/surface-cam` e manifesto |
| `output/surface-camera-kernel-x1p1-aarch64.tar.gz` | Kernel diagnóstico, DTB LCD, configuração, módulos em `usr/lib/modules` e manifesto; initramfs deve ser gerado no Fedora alvo |
| `output/surface-camera-SHA256SUMS` | Hashes dos bundles para conferir antes de extrair |

A ISO/kernel integrado experimental de commits anteriores permanece uma opção de teste. **Comece identificando o kernel em uso:** se já contém os drivers, o userspace pode ser testado sem instalar outro kernel. O kernel diagnóstico deste bundle serve para isolar a câmera; não é promoção do port de áudio protegido nem comprovação de segurança dos speakers.

[Fontes fixadas e receita de build/empacotamento](CAMERA_BUILD_REPRODUCTION.md). O bundle userspace final foi compilado com release/O2, stripped e suporte SoftISP GLES habilitado; a aceleração em hardware permanece sem teste físico. O helper C++ IMX681 foi exercitado para factory, black level e conversão de ganho. Os tars foram confrontados integralmente com seus manifestos: 45 arquivos/4 links no userspace e 3784 arquivos no kernel.

## 1. Primeiro teste: identificar e enumerar

No Fedora físico, como usuário da sessão GNOME:

```sh
uname -r
modinfo imx681
modinfo ov13858
modinfo qcom-camss
```

`7.2.8-arch1-3-sp11` é o kernel de trabalho anterior; não suponha que contém os novos drivers. `7.2.0-sp11-exp` identifica o candidato integrado previamente preparado, sujeito à conferência dos módulos. Se os drivers estiverem ausentes, use a entrada experimental já disponível ou a seção de kernel abaixo antes de testar captura.

Copie os bundles e o SHA256SUMS para uma pasta no Fedora. Dentro dela:

```sh
sha256sum -c surface-camera-SHA256SUMS || exit 1
camera_work="$HOME/surface-camera-test-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$camera_work" || exit 1
tar --no-same-owner -xzf surface-camera-userspace-f44-aarch64.tar.gz -C "$camera_work" || exit 1
export SURFACE_CAMERA_PREFIX="$camera_work/opt/surface-camera"
LD_LIBRARY_PATH="$SURFACE_CAMERA_PREFIX/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  ldd "$SURFACE_CAMERA_PREFIX/bin/cam"
"$camera_work/usr/local/bin/surface-cam" --list
```

Se `ldd` informar `not found`, resolva as dependências antes de capturar. No Fedora 44, o candidato usa `libevent`, `libtiff`, `libyaml`, `libdrm`, `systemd-libs`, `libglvnd-egl` e `libglvnd-gles`; o preview usa também GStreamer/plugins-base e o driver Mesa EGL da sessão. Esses pacotes do sistema não estão embutidos no tar. Envie o erro de carregamento se a enumeração não iniciar.

No repositório, `scripts/run-camera-candidate.sh` usa esse mesmo prefixo via `SURFACE_CAMERA_PREFIX` ou o staging local. Sem argumentos ele somente enumera. Recusa WSL, onde não existe o caminho CSI físico. O erro de enumeração no container sem `/sys/class/media` foi registrado como lacuna de ambiente, não como defeito do Surface.

Se o loader informar dependências ausentes, use os pacotes Fedora correspondentes; por exemplo, `libevent`, `libtiff`, `libyaml` e os pacotes GStreamer. Não copie bibliotecas do Ubuntu ou do Windows sobre `/usr/lib64`. A pilha candidata é carregada por processo e não exige substituir a libcamera do sistema para este teste.

## 2. Captura RAW e imagem processada

Antes de selecionar, envie/inspecione o `--list`: a frontal corresponde ao sensor IMX681, caminho CCI1/camera@1a; a traseira ao OV13858, CCI0/i2c-bus@1/camera@10. A câmera IR também pode aparecer. Não use índice 1/2 sem conferir a identidade.

Com os IDs reais listados, execute no mesmo Bash:

```sh
# Substitua pelos IDs exatos retornados por --list.
front_id='ID_FRONTAL_LISTADO'
rear_id='ID_TRASEIRO_LISTADO'
for selected_id in "$front_id" "$rear_id"; do
    timeout --signal=INT --kill-after=5 30 \
      "$camera_work/usr/local/bin/surface-cam" --camera "$selected_id" --info || exit 1
done
```

Registre os formatos e tamanhos efetivamente negociados. Para cada câmera, substitua `selected_id` pelo ID confirmado e `camera_label` por `front` ou `rear`:

```sh
selected_id="$front_id"
camera_label=front
capture_dir="$camera_work/$camera_label"
mkdir -m 700 "$capture_dir" || exit 1
timeout --signal=INT --kill-after=5 30 \
  "$camera_work/usr/local/bin/surface-cam" --camera "$selected_id" \
  --stream role=raw --capture=3 --metadata \
  --file="$capture_dir/raw-#.bin" > "$capture_dir/raw.log" 2>&1
capture_status=$?
printf 'capture exit: %s\n' "$capture_status"
[ "$capture_status" -eq 0 ] || exit 1
shopt -s nullglob
raw_frames=("$capture_dir"/raw-*.bin)
[ "${#raw_frames[@]}" -eq 3 ] || exit 1
for frame in "${raw_frames[@]}"; do [ -s "$frame" ] || exit 1; done
timeout --signal=INT --kill-after=5 30 \
  "$camera_work/usr/local/bin/surface-cam" --camera "$selected_id" \
  --stream role=viewfinder,pixelformat=RGB888 --capture=3 --metadata \
  --file="$capture_dir/preview-#.ppm" > "$capture_dir/preview.log" 2>&1 || exit 1
preview_frames=("$capture_dir"/preview-*.ppm)
[ "${#preview_frames[@]}" -eq 3 ] || exit 1
python3 - "$capture_dir" <<'PY' || exit 1
from pathlib import Path
import sys
for frame in sorted(Path(sys.argv[1]).glob('preview-*.ppm')):
    with frame.open('rb') as stream:
        assert stream.readline() == b'P6\n', frame
        width, height = map(int, stream.readline().split())
        assert width > 0 and height > 0, frame
        assert stream.readline() == b'255\n', frame
        assert frame.stat().st_size - stream.tell() == width * height * 3, frame
    print(frame.name, width, height, 'PPM completo')
PY
sha256sum "$capture_dir"/*.bin "$capture_dir"/*.ppm
```

Repita separadamente para a traseira, usando seu ID e uma pasta nova. Verifique exit codes e logs: timeout, frames ausentes ou zero bytes são falhas, não sucesso. Confirme tamanho com o formato/stride/bytesused negociados; largura×altura×bits sem considerar alinhamento não basta. Mude a cena de forma controlada para verificar frames distintos e examine os PPM localmente. Os registros Windows e RAW permitem comparar os modos, mas não provam calibração de cores.

Para preview nativo Wayland, com GStreamer e `waylandsink` disponíveis na sessão:

```sh
(
  export LD_LIBRARY_PATH="$SURFACE_CAMERA_PREFIX/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export LIBCAMERA_IPA_MODULE_PATH="$SURFACE_CAMERA_PREFIX/lib64/libcamera/ipa"
  export LIBCAMERA_IPA_PROXY_PATH="$SURFACE_CAMERA_PREFIX/libexec/libcamera"
  export LIBCAMERA_IPA_CONFIG_PATH="$SURFACE_CAMERA_PREFIX/share/libcamera/ipa"
  export GST_PLUGIN_PATH="$SURFACE_CAMERA_PREFIX/lib64/gstreamer-1.0${GST_PLUGIN_PATH:+:$GST_PLUGIN_PATH}"
  gst-inspect-1.0 libcamerasrc || exit 1
  gst-inspect-1.0 waylandsink || exit 1
  gst-launch-1.0 -e libcamerasrc camera-name="$front_id" ! videoconvert ! waylandsink
)
```

Encerre com Ctrl+C e repita com o ID traseiro. A carga do plugin foi verificada em container; o preview e a integração permanente GNOME/PipeWire ainda exigem teste físico. Não configure globalmente `LD_LIBRARY_PATH` nem substitua PAM para resolver câmera.

Colete o estado posterior:

```sh
python3 scripts/collect-camera-sensor-evidence.py
sudo journalctl -k -b -n 250 --no-pager > "$camera_work/kernel-after-capture.log"
```

Registre indicador de privacidade, sensor/modo/formato, contagem e hashes, cadência, imagens processadas e mensagens de CAMSS/CCI/CSIPHY/IOMMU. Depois de captura básica, faltam repetição start/stop, suspensão/retomada e uso concorrente. Frames e logs ficam privados; envie primeiro o resumo e os erros.

## 3. Kernel diagnóstico, quando necessário

A instalação no Fedora precisa criar um initramfs com suas dependências reais. Confirme espaço em `/boot`, mantenha a entrada de trabalho e faça estas operações somente no Fedora instalado. Pare se qualquer destino já existir; não sobrescreva um candidato anterior.

```sh
camera_kver=7.2.0-sp11-camera-x1p1
kernel_work="$camera_work/kernel"
mkdir -m 700 "$kernel_work" || exit 1
tar --no-same-owner -xzf surface-camera-kernel-x1p1-aarch64.tar.gz -C "$kernel_work" || exit 1
sudo test ! -e "/usr/lib/modules/$camera_kver" || exit 1
for target in /boot/vmlinuz-sp11-camera /boot/initramfs-sp11-camera.img \
  "/boot/config-$camera_kver" /boot/dtb-sp11/qcom/x1p64100-microsoft-denali-camera.dtb; do
    sudo test ! -e "$target" || exit 1
done
sudo cp -R --no-preserve=ownership "$kernel_work/usr/lib/modules/$camera_kver" /usr/lib/modules/ || exit 1
sudo install -m 644 "$kernel_work/boot/vmlinuz-sp11-camera" /boot/vmlinuz-sp11-camera || exit 1
sudo install -m 644 "$kernel_work/boot/config-$camera_kver" "/boot/config-$camera_kver" || exit 1
sudo install -d /boot/dtb-sp11/qcom || exit 1
sudo install -m 644 "$kernel_work/boot/dtb-sp11/qcom/x1p64100-microsoft-denali-camera.dtb"   /boot/dtb-sp11/qcom/x1p64100-microsoft-denali-camera.dtb || exit 1
sudo depmod "$camera_kver" || exit 1
sudo dracut --kver "$camera_kver" /boot/initramfs-sp11-camera.img || exit 1
sudo lsinitrd /boot/initramfs-sp11-camera.img > /dev/null || exit 1
sudo lsinitrd /boot/initramfs-sp11-camera.img | less
```

Confira no initramfs os módulos de boot, armazenamento, firmware e LUKS/Btrfs necessários. A existência/legibilidade do arquivo não garante boot. Para teste **uma vez**, no GRUB edite uma entrada Surface que já inicializa: conserve seus UUIDs, rootflags, parâmetros de hardware e dispositivos; substitua somente os nomes de kernel, initramfs e DTB pelos nomes `*-sp11-camera`/`*-denali-camera.dtb` copiados acima. Preserve os prefixos de partição/diretório da entrada existente. Não torne esse kernel default antes de verificar boot e câmera. No boot de teste confirme `uname -r` igual a `$camera_kver` antes de interpretar qualquer resultado.

Para recuperação, inicialize a entrada anterior. Remover o candidato deve ocorrer somente após confirmar que ele não está em uso; os caminhos exclusivos permitem distinguir seus arquivos. O bundle não contém chaves Secure Boot nem headers para módulos externos; essas dependências precisam ser tratadas se a instalação as exigir.

## Limitações específicas ainda abertas

O módulo Windows traseiro identifica atuador `dw9800` e EEPROM `st_m24c64`. O DT candidato não possui `lens-focus`/nó desse atuador. Logo, autofocus/calibração por unidade não podem ser declarados habilitados por esta compilação. A frontal não informa atuador. A diferença de fase/crop traseira e o CCM frontal sem calibração completa também permanecem sob investigação. Primeiro a captura física localizará o próximo bloqueio real.
