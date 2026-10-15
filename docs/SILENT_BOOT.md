# Boot e desligamento discretos no Fedora instalado

Estas instruções se aplicam ao Fedora 44 instalado no Surface. Não execute em WSL, chroot de construção ou sessão live. Não há implantação automática nem reconstrução da ISO. O boot físico e a continuidade visual do logotipo continuam pendentes.

## Identificar e salvar a instalação

```sh
python3 scripts/collect-fedora-session.py --section boot
uname -r
cat /proc/cmdline
findmnt --target /
findmnt --target /boot
findmnt --target /boot/efi
sudo sha256sum /boot/vmlinuz-sp11 /boot/initramfs-sp11.img /boot/dtb-sp11/qcom/x1p64100-microsoft-denali.dtb
sudo lsinitrd /boot/initramfs-sp11.img > /dev/null || exit 1
sudo lsinitrd /boot/initramfs-sp11.img | less || exit 1
sudo cat /etc/grub.d/09_surface_sp11
```

A entrada `surface-sp11` deste projeto carrega `/boot/vmlinuz-sp11`, `/boot/initramfs-sp11.img` e o DTB explicitamente. É gerada por `/etc/grub.d/09_surface_sp11`, com argumentos de `GRUB_CMDLINE_LINUX` e `GRUB_CMDLINE_LINUX_DEFAULT`. `grubby` altera entradas BLS e não atualiza esta entrada personalizada. Não edite `boot/grub/grub.cfg` do repositório para mudar o sistema instalado.

Execute os blocos abaixo na mesma sessão Bash e pare em qualquer erro; as variáveis e a função de restauração precisam continuar disponíveis. Antes de modificar, mantenha a mídia de recuperação disponível, confirme espaço livre em `/boot` e faça backup:

```sh
set -o pipefail
# Verifique disponibilidade antes de editar qualquer configuração.
available_themes=$(plymouth-set-default-theme --list) || exit 1
printf '%s\n' "$available_themes" | grep -Fxq bgrt || { echo 'Tema bgrt indisponível; pare antes de alterar.' >&2; exit 1; }
previous_theme=$(plymouth-set-default-theme) || exit 1
[ -n "$previous_theme" ] || exit 1
boot_backup="/var/backups/surface-boot-$(date -u +%Y%m%dT%H%M%SZ)"
sudo mkdir -m 700 "$boot_backup" || exit 1
sudo cp -a /etc/default/grub /etc/grub.d/09_surface_sp11 /boot/grub2/grub.cfg /boot/initramfs-sp11.img "$boot_backup/" || exit 1
sudo cp -a /etc/plymouth "$boot_backup/" || exit 1
printf '%s\n' "$previous_theme" | sudo tee "$boot_backup/previous-theme" >/dev/null || exit 1
restore_boot() {
    sudo cp -a "$boot_backup/grub" /etc/default/grub || return 1
    sudo cp -a "$boot_backup/09_surface_sp11" /etc/grub.d/09_surface_sp11 || return 1
    sudo cp -a "$boot_backup/initramfs-sp11.img" /boot/initramfs-sp11.img || return 1
    sudo cp -a "$boot_backup/grub.cfg" /boot/grub2/grub.cfg || return 1
    sudo cp -a "$boot_backup/plymouth/." /etc/plymouth/ || return 1
    sudo plymouth-set-default-theme "$previous_theme" || return 1
    sudo grub2-script-check /boot/grub2/grub.cfg || return 1
}
stop_and_restore() {
    restore_boot || { echo "RESTAURAÇÃO FALHOU: use recuperação e o backup $boot_backup; não reinicie." >&2; exit 1; }
    echo 'Estado anterior restaurado; pare e investigue a falha antes de reiniciar.' >&2
    exit 1
}
```

Anote o tema retornado e a localização do backup. Registre `uname -r`, mas não suponha que ele identifica o kernel fixado quando a entrada inicializada foi outra.

## Alterar somente os argumentos de aparência

Abra `sudoedit /etc/default/grub`. Nas duas variáveis de argumentos, remova tokens `earlycon=...`, `earlycon`, `keep_bootcon`, `loglevel=7`, outros `loglevel=...`, `ignore_loglevel`, `rd.debug`, `debug`, `systemd.log_level=debug`, `rd.plymouth=0` e `plymouth.enable=0`. Remova também valores conflitantes de quiet/splash/status/udev, se existirem. Acrescente uma vez:

```text
quiet splash loglevel=0 systemd.show_status=false rd.systemd.show_status=false udev.log_level=err rd.udev.log_level=err
```

Preserve UUIDs, `rootflags`/subvolume Btrfs, `rd.luks.*`, resume, consoles necessários à recuperação e flags de hardware. O gerador mantém/inclui `clk_ignore_unused pd_ignore_unused arm64.nopauth systemd.mask=tpm2.target`; não os remova. Preserve a senha de criptografia e os caminhos de recuperação. Não adicione `rd.shell=0` nem suprima mecanismos de emergência.

A ISO atual contém `earlycon=efifb keep_bootcon loglevel=7 rd.plymouth=0 plymouth.enable=0`: eles conflitam com boot discreto e podem ter sido herdados durante instalação. Mudar o instalado não altera a ISO.

## Tema e initramfs correto

```sh
plymouth-set-default-theme --list || exit 1
```

O check anterior deve confirmar `bgrt` listado antes de qualquer mudança. Se não estiver, pare, registre a lacuna e consulte `dnf info plymouth-theme-bgrt` antes de instalar explicitamente o pacote da distribuição. O tema Fedora deste rootfs usa o módulo `two-step` e `UseFirmwareBackground=true` em boot, shutdown e reboot. Isso depende de BGRT fornecido pelo firmware:

```sh
ls -ld /sys/firmware/acpi/bgrt
cat /sys/firmware/acpi/bgrt/status
```

Boot via Device Tree pode não expor BGRT. Nesse caso, continuidade exata do logotipo OEM está pendente de ativo fornecido pelo proprietário e teste no painel físico. Um tema próprio pode usar uma imagem autorizada, mas exige testar escala, transições e diálogo LUKS; não há garantia de ausência de tela preta entre firmware, GRUB, DRM e GNOME.

Para esta imagem, o kernel fixado é `7.2.8-arch1-3-sp11`. Confirme que o kernel copiado corresponde à árvore de módulos antes de reconstruir; pare se não corresponder:

```sh
surface_kver=7.2.8-arch1-3-sp11
test -d "/usr/lib/modules/$surface_kver" || exit 1
sudo cmp /boot/vmlinuz-sp11 "/usr/lib/modules/$surface_kver/vmlinuz" || exit 1
sudo plymouth-set-default-theme bgrt || stop_and_restore
# Não usa -R: a reconstrução automática pode escolher outro kernel/initramfs.
sudo dracut --force --no-hostonly --add plymouth --kver "$surface_kver" /boot/initramfs-sp11.img || stop_and_restore
sudo lsinitrd /boot/initramfs-sp11.img > /dev/null || stop_and_restore
sudo lsinitrd /boot/initramfs-sp11.img | less || stop_and_restore
```

Falha na seleção de tema, reconstrução ou validação executa `stop_and_restore`, restaurando imediatamente o initramfs, configuração e GRUB salvos antes de parar. Verifique no `lsinitrd` o kernel esperado, Plymouth/tema, drivers/firmware Surface e suporte LUKS/Btrfs necessários. Preserve os arquivos em `/etc/dracut.conf.d/`; não substitua a configuração de hardware pela configuração de um computador genérico. Se `cmp` falhar porque a instalação usa outra revisão, identifique sua proveniência antes de prosseguir; não escolha a versão apenas pelo nome do arquivo.

```sh
sudo grub2-mkconfig -o /boot/grub2/grub.cfg || stop_and_restore
sudo grub2-script-check /boot/grub2/grub.cfg || stop_and_restore
sudo less /boot/grub2/grub.cfg
sudo sha256sum /boot/vmlinuz-sp11 /boot/initramfs-sp11.img /boot/dtb-sp11/qcom/x1p64100-microsoft-denali.dtb
```

Na entrada `surface-sp11`, confirme os argumentos, UUID/rootflags, caminhos e DTB. Nunca gere em `/boot/efi/EFI/fedora/grub.cfg`: esse arquivo é o stub do fornecedor. Mantenha o menu acessível e seu timeout; não esconda o único caminho de recuperação.

## Verificação física e recuperação

No próximo boot, observe firmware → menu → Plymouth → senha LUKS → GDM → GNOME. Confirme `/proc/cmdline`, repita o coletor e inspecione `journalctl -b -p warning` e `journalctl -k -b`; reduzir mensagens na tela não deve desabilitar o journal. Registre flashes, duração de telas pretas e prompts. Para shutdown/reboot, salve o trabalho, observe cada transição e, no boot seguinte, consulte `journalctl -b -1` se o journal anterior estiver disponível. Se não estiver, registre essa lacuna; não conclua que não houve erros.

No menu GRUB, pressione `e`, remova temporariamente `quiet splash loglevel=0` e os tokens de ocultação de status, adicione `loglevel=7 systemd.show_status=true rd.systemd.show_status=true plymouth.enable=0`, então inicialize com Ctrl+X. Isso só vale para aquele boot. Em falha grave use mídia de recuperação para montar a instalação, inclusive desbloquear LUKS, e restaurar o backup; não formate partições.

Para rollback persistente, defina `boot_backup` para o diretório exato anotado (a variável não sobrevive ao reboot). Execute no sistema instalado ou no ambiente de recuperação já montado/chroot correto:

```sh
# Substitua pelo diretório real, sem criar um novo backup neste ponto.
boot_backup=/var/backups/surface-boot-DATA_ANOTADA
sudo test -s "$boot_backup/initramfs-sp11.img" || exit 1
sudo cp -a "$boot_backup/grub" /etc/default/grub || exit 1
sudo cp -a "$boot_backup/09_surface_sp11" /etc/grub.d/09_surface_sp11 || exit 1
sudo cp -a "$boot_backup/initramfs-sp11.img" /boot/initramfs-sp11.img || exit 1
sudo cp -a "$boot_backup/plymouth/." /etc/plymouth/ || exit 1
# Leia o tema anterior registrado no backup:
previous_theme=$(sudo cat "$boot_backup/previous-theme") || exit 1
[ -n "$previous_theme" ] || exit 1
sudo plymouth-set-default-theme "$previous_theme" || exit 1
sudo grub2-mkconfig -o /boot/grub2/grub.cfg || { sudo cp -a "$boot_backup/grub.cfg" /boot/grub2/grub.cfg || exit 1; exit 1; }
sudo grub2-script-check /boot/grub2/grub.cfg || { sudo cp -a "$boot_backup/grub.cfg" /boot/grub2/grub.cfg || exit 1; exit 1; }
```

A cópia exata do initramfs anterior dispensa reconstruí-lo no rollback. Se a geração falhar, a cópia `grub.cfg` salva permite restaurar `/boot/grub2/grub.cfg` ao estado anterior. Confirme caminhos e entrada antes de reiniciar. Preserve o backup até o teste físico passar.

Prompts de criptografia, firmware, segurança e falhas podem permanecer visíveis e necessários. Não há promessa de esconder toda saída nem de logo contínuo sob DT.

Referências primárias: [Fedora GRUB](https://docs.fedoraproject.org/en-US/quick-docs/grub2-bootloader/), [dracut](https://www.kernel.org/pub/linux/utils/boot/dracut/dracut.html), além do gerador `boot/grub/09_surface_sp11` e tema BGRT da imagem auditados localmente. Verifique a documentação correspondente às versões instaladas.
