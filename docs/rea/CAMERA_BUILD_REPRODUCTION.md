# Reproduzir o candidato de câmera

Receita do checkpoint de 2026-10-15, em Fedora 44 AArch64. O resultado é um **candidato para teste físico**, sem instalação automática nem mudança do kernel padrão. Reproduzir a receita não garante hashes binários idênticos: timestamps, toolchain e chave de assinatura IPA podem mudar. Os manifestos dos bundles descrevem os binários efetivamente entregues.

## Fontes fixadas

| Entrada | Revisão / SHA256 do arquivo usado |
|---|---|
| Linux, repositório `torvalds/linux` | commit `548e7bcd0c5460ddcbca9600cea603ebeebf4da7`; tar.gz `9d34c13e30b54bb139779fb3fac0c64f1634ffd6340b6258c8dfde90dbbfc2ce` |
| Port Surface, `turbineBMW/surface-pro-11-linux` | commit `15e590c3c3298dd75a0b79256efa815c15dc0897` |
| `kernel/port-7.3/sp11-port-7.3.patch` desse port | `16cdb32c732dde20f088c27bd1b83b269e631999c76edf1045126ff220ed3010` |
| `kernel/port-7.3/config` desse port | `7798b8bebf2d286c0dfea770d357ceea7ff3b6e55c14bcb70cf5dfad6dc2d011` |
| libcamera, `kbingham/libcamera` | tag `v0.7.0`, commit `b7854fd07d42168f099b5ce30d1702e0e0875bf5`; tar.gz `40530d976d18678693283ccf011f4b29f5110b3ae90f2b8ec5250f18fdf2e075` |

O libcamera foi obtido do fork pessoal do mantenedor, pois os downloads canônicos disponíveis nesta sessão retornavam HTML de proteção. A API GitHub informa assinatura válida do tag; não houve validação local independente contra o repositório canônico. A versão Fedora instalada também era 0.7.0.

URLs de entrada (use revisões completas, não branches móveis):

```text
https://github.com/torvalds/linux/archive/548e7bcd0c5460ddcbca9600cea603ebeebf4da7.tar.gz
https://raw.githubusercontent.com/turbineBMW/surface-pro-11-linux/15e590c3c3298dd75a0b79256efa815c15dc0897/kernel/port-7.3/sp11-port-7.3.patch
https://raw.githubusercontent.com/turbineBMW/surface-pro-11-linux/15e590c3c3298dd75a0b79256efa815c15dc0897/kernel/port-7.3/config
https://github.com/kbingham/libcamera/archive/refs/tags/v0.7.0.tar.gz
```

Baixe em diretório novo e confira com `sha256sum` antes de extrair. Nesta sessão a rede Linux teve erros TLS e os downloads foram feitos pelo PowerShell Windows; os hashes acima são dos arquivos recebidos, não de respostas HTML. Guarde logs e a lista de RPMs/toolchain usados.

## Kernel

Dependências usadas: GCC 16.2.1, binutils, make, bison, flex, bc, OpenSSL-devel, elfutils-libelf-devel, dwarves, Python3 e depmod. O container Fedora montava este repositório em `/workspace`. Os comandos abaixo usam variáveis absolutas apontando para uma extração limpa (`kernel_src`), diretório de build novo (`kernel_build`), staging novo (`kernel_stage`), cópia do port (`port_src`) e este repositório (`repo`). Não use a árvore parcial `linux-camera-only-548e7bcd`.

```sh
patch --fuzz=0 -d "$kernel_src" -p1 < "$port_src/kernel/port-7.3/sp11-port-7.3.patch"
patch --fuzz=0 -d "$kernel_src" -p1 < "$repo/patches/kernel/0004-sp11-camera-rear-endpoint.patch"
mkdir "$kernel_build" "$kernel_stage"
cp "$port_src/kernel/port-7.3/config" "$kernel_build/.config"
make -C "$kernel_src" O="$kernel_build" ARCH=arm64 LOCALVERSION=-sp11-camera-x1p1 olddefconfig
make -j4 -C "$kernel_src" O="$kernel_build" ARCH=arm64 LOCALVERSION=-sp11-camera-x1p1 \
  Image modules qcom/x1p64100-microsoft-denali.dtb
make -C "$kernel_src" O="$kernel_build" ARCH=arm64 LOCALVERSION=-sp11-camera-x1p1 \
  INSTALL_MOD_PATH="$kernel_stage" INSTALL_MOD_STRIP=1 modules_install
```

Confirme `make ... kernelrelease` = `7.2.0-sp11-camera-x1p1`. O config resultante usado nesta entrega tem SHA256 `a02ffb8ce3ba6b4eed615e636d836d0dc709d6b446c04bb4dc4b758358a1ed38`; está incluído em `boot/config-7.2.0-sp11-camera-x1p1`. O nome “port-7.3” não altera a versão interna 7.2.0 da árvore base. Nenhum patch de áudio foi aplicado nesta árvore limpa.

No staging, normalize **somente a árvore recém-criada** para o layout Fedora `usr/lib/modules`, retire links `build`/`source` que apontam para a máquina de build e execute `depmod -b "$kernel_stage" 7.2.0-sp11-camera-x1p1`. Copie:

- `arch/arm64/boot/Image` → `boot/vmlinuz-sp11-camera`;
- `.config` → `boot/config-7.2.0-sp11-camera-x1p1`;
- `arch/arm64/boot/dts/qcom/x1p64100-microsoft-denali.dtb` → `boot/dtb-sp11/qcom/x1p64100-microsoft-denali-camera.dtb`.

Verifique todos os módulos com `modinfo -F vermagic`: foram 3767, todos `7.2.0-sp11-camera-x1p1 SMP preempt mod_unload aarch64`. Inspecione o DTB com `fdtget`/`dtc` para resets, clocks, endpoints e backlight. Não inclua no tar o link `lib -> usr/lib`: o Fedora alvo já tem seu próprio link. O initramfs é gerado **no Fedora alvo** com seu storage/firmware; veja o [procedimento de instalação e recuperação](CAMERA_INTEGRATION_STATUS.md).

## libcamera

Dependências usadas no container Fedora: meson, ninja-build, gcc-c++, python3-ply, python3-jinja2, python3-pyyaml, pkgconf, libyaml-devel, openssl-devel, libevent-devel, libdrm-devel, libtiff-devel, systemd-devel, gstreamer1-devel, gstreamer1-plugins-base-devel e libglvnd-devel. Os RPMs recebidos foram conferidos com `rpmkeys --checksig` antes de instalar no container. Resolva os nomes presentes no repositório Fedora; a lista não é um lockfile de RPMs.

Use fonte libcamera limpa, build e staging novos (`camera_src`, `camera_build`, `camera_stage`):

```sh
for patch_file in "$repo"/patches/libcamera/*.patch; do
    patch --fuzz=0 -d "$camera_src" -p1 < "$patch_file" || exit 1
done
meson setup "$camera_build" "$camera_src" \
  --prefix=/opt/surface-camera --libdir=lib64 \
  --buildtype=release -Doptimization=2 -Db_ndebug=true \
  -Dpipelines=simple,uvcvideo -Dipas=simple -Dcam=enabled \
  -Dgstreamer=enabled -Dudev=enabled -Dv4l2=auto \
  -Dqcam=disabled -Dpycamera=disabled -Ddocumentation=disabled \
  -Dtest=false -Dtracing=disabled -Dlc-compliance=disabled
meson compile -j4 -C "$camera_build"
DESTDIR="$camera_stage" meson install --strip --no-rebuild -C "$camera_build"
install -Dm755 "$repo/scripts/run-camera-candidate.sh" "$camera_stage/usr/local/bin/surface-cam"
```

Confira no resumo Meson **SoftISP GPU acceleration: true**. EGL/GLES encontrados na compilação habilitam esse caminho, mas a aceleração Adreno ainda precisa ser validada fisicamente. Se instalou headers após configurar, use `meson setup --clearcache --reconfigure` antes de recompilar.

Hashes dos patches importados, preservando autoria/licença:

```text
0eca076df0af51bd65815cda6318c7581477b54ef4a6e2daffcaa3843c1428cd  0001-libcamera-camera_sensor_properties-Add-IMX681.patch
383aa97756d1e8cb30eb20abb06b9a35049a095265e7f1a96ec92ad817ccc166  0002-libipa-camera_sensor_helper-Add-IMX681.patch
c8e93aa9795c1269bc9ff68735b825a98828c1356811e2aa5bd672d4dd07ffc5  0003-ipa-simple-Add-initial-IMX681-tuning-data.patch
```

Validação sem câmera: `ldd` do `cam` e do plugin com `LD_LIBRARY_PATH` do staging, sem dependências ausentes; `cam --help`; `gst-inspect-1.0 libcamerasrc` com `GST_PLUGIN_PATH` do staging deve informar o arquivo desse staging. O launcher sobrescreve os caminhos IPA herdados e valida os componentes necessários antes de executar. A descoberta efetiva de tuning durante streaming depende do teste físico.

## Manifestos e empacotamento

Nos stagings, o manifesto JSON enumera cada arquivo regular (caminho relativo, bytes e SHA256), cada symlink (alvo relativo), fontes, patches e opções de build. Não liste o próprio manifesto recursivamente. `hardware_validated` deve permanecer `false` até cumprir a aceitação física. Guarde também `meson-info/intro-buildoptions.json`, `.config`, versões do compilador e logs.

```sh
# Após gerar/verificar os manifestos nos respectivos stagings:
tar -C "$kernel_stage" -czf "$repo/output/surface-camera-kernel-x1p1-aarch64.tar.gz" \
  boot usr/lib/modules surface-camera-kernel-manifest.json
tar -C "$camera_stage" -czf "$repo/output/surface-camera-userspace-f44-aarch64.tar.gz" \
  opt usr/local/bin/surface-cam surface-camera-userspace-manifest.json
(cd "$repo/output" && sha256sum surface-camera-kernel-x1p1-aarch64.tar.gz \
  surface-camera-userspace-f44-aarch64.tar.gz > surface-camera-SHA256SUMS)
```

Antes de distribuir, confronte o conteúdo de cada tar com todos os hashes/links do manifesto e recuse caminhos absolutos, `..`, devices ou links que escapem do pacote. A entrega desta sessão foi verificada desse modo. Não inclua Windows SYS/BIN, calibração privada, pseudocódigo REA ou frames nos bundles públicos/Git. Os bundles são locais e não foram publicados.
