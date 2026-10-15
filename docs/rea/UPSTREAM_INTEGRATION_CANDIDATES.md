# Candidatos de integração: câmera, sensores e áudio

Consulta em 2026-10-15. São fontes para auditoria e compilação isolada; nenhuma
foi implantada no Fedora do usuário. O funcionamento relatado pelos autores não
é validação no nosso X1P/LCD.

## Câmeras e libcamera

Repositório: [turbineBMW/surface-pro-11-linux](https://github.com/turbineBMW/surface-pro-11-linux/tree/15e590c3c3298dd75a0b79256efa815c15dc0897),
revisão `15e590c3c3298dd75a0b79256efa815c15dc0897`.

- [Patch de kernel](https://github.com/turbineBMW/surface-pro-11-linux/blob/15e590c3c3298dd75a0b79256efa815c15dc0897/kernel/port-7.3/sp11-port-7.3.patch):
  SHA256 `16cdb32c732dde20f088c27bd1b83b269e631999c76edf1045126ff220ed3010`.
- Base mainline `548e7bcd0c5460ddcbca9600cea603ebeebf4da7`, existência e data
  confirmadas pela API de commits de torvalds/linux: 2026-08-28. A árvore se
  identifica como 7.2.0 durante a janela de merge 7.3; o nome do perfil não
  significa que seja um kernel estável 7.3.
- [BUILDINFO](https://github.com/turbineBMW/surface-pro-11-linux/blob/15e590c3c3298dd75a0b79256efa815c15dc0897/kernel/port-7.3/BUILDINFO)
  declara tip `1cd9ebdd1584403e14408de1c559883acf064cc6`, tree
  `1f776364a949e575bfdc72ad1b8c92a7d7f97b30` e configuração SHA256
  `7798b8bebf2d286c0dfea770d357ceea7ff3b6e55c14bcb70cf5dfad6dc2d011`.
- A inspeção local do patch encontrou CAMSS X1E, drivers IMX681/OV13858/VD55G0
  e mudanças no DTS comum Denali. Seus resets usam 237/110/109, coerentes com
  os primeiros inteiros TLMMGPIO que recuperamos dos recursos Windows.
  Isso oferece corroboracão entre fontes, sem provar o mapeamento elétrico no
  aparelho do usuário.
- O [registro de revisão de câmera](https://github.com/turbineBMW/surface-pro-11-linux/blob/15e590c3c3298dd75a0b79256efa815c15dc0897/docs/CAMERA-REVIEW.md)
  diferencia a série revisada de históricos retirados e registra origens de
  drivers/tabelas. Preservar as licenças e essa delimitação durante importação.
- O [estado libcamera](https://github.com/turbineBMW/surface-pro-11-linux/blob/15e590c3c3298dd75a0b79256efa815c15dc0897/userspace/libcamera/README.md)
  separa patches históricos para 0.7.1 do uso relatado de 0.7.2-3 mais tuning
  IMX681. Verificar a versão efetiva do Fedora antes de aplicar patches já
  incorporados; falta de calibração completa de cores continua documentada.

A base exata foi extraída em árvore isolada e `patch --dry-run --batch -p1`
aceitou todos os hunks (exit 0). O arquivo-fonte tem SHA256
`9d34c13e30b54bb139779fb3fac0c64f1634ffd6340b6258c8dfde90dbbfc2ce`;
o registro está em `output/kernel-integration/source-preparation.json`.
A aplicação efetiva posterior também passou com `--fuzz=0`. Isso verifica
aplicação textual, não compilação nem funcionamento físico.

O próximo passo é aplicar efetivamente o patch nessa árvore, auditar
o DTB LCD e seus reguladores/backlight, compilar e comparar interfaces. Não
trocar o DTB LCD por um DTB OLED de release. A integração deve conservar o boot
conhecido e oferecer uma entrada candidata separada.

## Áudio protegido

Repositório: [geocausa/SP11X1e-audio](https://github.com/geocausa/SP11X1e-audio/tree/3232e1dacdeb580a10a9cb8d4756a4518a7bd83e),
revisão `3232e1dacdeb580a10a9cb8d4756a4518a7bd83e`.

A [análise de proteção](SPEAKER_PROTECTION_FINDINGS.md) registra a correspondência
exata do ACDB REV_0D e a reprodução binária da topologia FullIO v19c no Fedora44.
Sua cadeia de kernel protegida parte de 7.1.5 e não é intercambiável com a série
de câmera acima. Reconciliar os patches/interfaces e a configuração de ambos é
trabalho de integração, não uma cópia de topologia ou módulos.

A cadeia protegida Golden-v32/v33 teve 42 arquivos de fontes e metadados
recuperados da revisão fixada, com hashes em
`output/upstream-research/protected-kernel-sources.json`. O overlay inclui
AudioReach/q6apm, WSA884x, LPASS, SoundWire e DT; os patches posteriores
0069–0072 e o delta de microfone precisam ser reconciliados com a base de câmera.
Nenhum script externo de instalação/reprodução foi executado. Os seis patches
posteriores conferiram com os manifestos e aplicaram com `--fuzz=0` sobre o
overlay protegido. A comparação de três vias com a base de câmera produziu
15 arquivos sem conflitos e sete com conflitos em 22 arquivos selecionados;
nenhum resultado dessa mesclagem foi promovido ao kernel de uso.
Resultados: `output/kernel-integration/protected-audio-7.1.5-final/patch-results.json`
e `output/kernel-integration/audio-three-way-review/merge-results.json`.
DT, bindings e configuração ainda exigem conciliação além desses arquivos.

## Sensores e autenticação

Os relatos de sensor de cor/ALS do candidato precisam ser acompanhados até o
daemon, firmware e interface usados. Um HID genérico ou `iio-sensor-proxy`
instalado não prova transporte funcional. Howdy continua dependente de IR
funcional e integração de autenticação testada com recuperação por senha.

## Retenção local

As árvores de arquivos, revisões, textos e patches selecionados estão em
`output/upstream-research/`, ignorado pelo Git. Binários Windows, ACDB e logs
permanecem locais. Um futuro patch incorporado ao projeto deverá ter origem,
licença/autoria e revisão de código preservadas nos próprios artefatos.
