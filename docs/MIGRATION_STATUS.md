# Migração permanente para Fedora: estado das fases

Meta: concluir habilitação de hardware, qualidade de áudio com proteção real dos
alto-falantes, boot/shutdown silenciosos, GNOME/Wayland/Material 3 e organização
do repositório. A meta permanece **ativa**. Documentação, compilação e testes
locais não substituem validação no Fedora físico.

## Evidência necessária e situação atual

| Fase | Entrega e critério de conclusão | Evidência atual | Situação |
|---|---|---|---|
| Câmeras / ISP / IR | Identificação, recursos, drivers e pipeline; captura reproduzível no Fedora e comportamento do indicador/iluminação | 142 arquivos inventariados; oito módulos Chromatix decodificados; 1151 funções recuperadas via REA; kernel e libcamera/GStreamer candidatos compilados | Captura e aplicativos no Fedora físico ainda pendentes |
| ALS | Transporte e driver identificados, leitura de luz e integração com sensor proxy verificadas | Plataforma de sensores Windows associada a qcSensors/FastRPC/QMI; transporte Linux ainda sem captura | Pendente de enumeração Fedora e análise do candidato de sensores |
| Howdy | IR funcional antes de integrar autenticação; configuração com recuperação por senha e teste de login | Roteiro de pré-requisitos; nenhuma alteração PAM | Pendente do pipeline IR |
| Áudio | Perfil/UCM e canais corretos, ausência de falhas; proteção DSP/VI/calibração do alto-falante demonstrada antes de ampliar ganho | Usuário relata speakers e microfone funcionando; fonte de proteção X1E auditada, ACDB REV_0D idêntico e topologia recompilada com hash publicado; port X1P ainda pendente | Diagnóstico e portabilidade em andamento; proteção não declarada implementada |
| Boot e shutdown | GRUB + initramfs + Plymouth corretos e sequência visual OEM verificada fisicamente | Caminho customizado de GRUB identificado; guia entregue; disponibilidade BGRT no Linux desconhecida | Pendente de aplicação/observação Fedora |
| GNOME / Wayland | Sessão e apps identificados por protocolo; tema, paleta dinâmica e ícones aplicados com compatibilidade da versão | Base Workstation 44 / GNOME 50; guia e coletor entregues | Pendente de evidência da sessão e aplicação do tema |
| Git | Estrutura, scripts, ignore, histórico e comandos de publicação | Commits cf57f88 e 84c3dcc; guia do repositório; arquivos privados ignorados | Estrutura entregue; publicação manual depende da URL do usuário |

## Trabalho concluído

- [Inicialização e organização Git](REPOSITORY_SETUP.md).
- [Plano REA/BMAD de câmeras e sensores](rea/PHASE_1_CAMERA_SENSORS.md).
- [Identificação Windows e recursos de câmera](rea/CAMERA_RESOURCE_FINDINGS.md).
- Decoder testado e reconstrução exata dos seis arquivos originais.
- Enumeração Windows confirmou CPU `X1P64100`, sensores de câmera com os IDs
  MSHW0490/0491/0492 e áudio MSHW0486/REV_0D. Isso não comprova binding Linux.

## Guias e análise entregues nesta continuação

- [Áudio e UCM/PipeWire](AUDIO_DIAGNOSTICS.md).
- [Speaker protection com REA](rea/SPEAKER_PROTECTION_FINDINGS.md).
- [Boot/shutdown e Plymouth](SILENT_BOOT.md).
- [Wayland e Material 3](GNOME_MATERIAL3.md).
- [Candidatos de integração kernel/libcamera/áudio](rea/UPSTREAM_INTEGRATION_CANDIDATES.md).

O guia visual identifica explicitamente a falta de compatibilidade GNOME50 nas
extensões Material You/Open Bar consultadas. Paleta/ícones e CSS experimentais
não completam sozinhos uma adaptação integral de Shell e aplicativos a Material3.

## Próximas execuções

1. Auditar e preparar a integração dos candidatos de câmera/ISP/libcamera e de
   áudio protegido em kernel separado, preservando o kernel/ISO que já funciona.
2. Comparar a calibração de áudio do próprio aparelho com a revisão exigida pelo
   candidato; registrar diferenças de firmware, topologia e ABI do kernel.
3. Executar os coletores no Fedora como usuário da sessão, analisar as lacunas e
   aplicar os guias de áudio/boot/GNOME somente nos caminhos que correspondem à
   instalação real.
4. Validar as funções físicas e atualizar esta tabela com as capturas e versões
   efetivamente testadas. Não marcar as fases como completas pela presença de
   um módulo, arquivo de topologia, nó `/dev/video*` ou teste sintético.

O workspace atual executa WSL. Foi solicitado acesso SSH ao Fedora ou o resumo
da coleta física; enquanto isso, análise estática e preparação de integração
continuam disponíveis.

## Continuação: câmera frontal e traseira

A prioridade atual é a câmera, conforme nova orientação do usuário. Veja [REA dos módulos Windows](rea/CAMERA_WINDOWS_MODULE_FINDINGS.md) e [candidato compilado e teste físico](rea/CAMERA_INTEGRATION_STATUS.md). A frontal tem tabelas de inicialização/modo idênticas às do Windows; na traseira resta uma diferença de crop/fase e o atuador DW9800 ainda não está ligado no DT. Nenhuma dessas evidências substitui a captura física.
