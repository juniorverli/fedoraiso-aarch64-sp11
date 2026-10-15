# Câmeras: REA dos módulos Windows e confronto com CAMSS

Investigação em 2026-10-15. **Ainda sem captura física no Fedora deste Surface.** O objetivo continua sendo frontal e traseira funcionando; este registro documenta evidência obtida durante a implementação, sem declarar conclusão.

## Cobertura real

O inventário ampliado abrange todos os arquivos dos 20 diretórios `qccam*` e `surfacecam*` presentes no DriverStore local: **142 arquivos / 109811619 bytes**, incluindo CAT/INF, drivers, DLLs, módulos, tuning e firmware. Cada arquivo recebeu SHA256. Inventariar não significa interpretar todo seu conteúdo. O inventário, pseudocódigo, calibração e dados extraídos ficam privados em `output/camera-rea-full/`.

O REA 6.5.0 foi configurado com Ghidra 12.1.4 e JDK AArch64 25.0.4.1. O release oficial Ghidra foi conferido contra o digest SHA256 `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`; seu decompilador nativo AArch64 foi compilado localmente com `make -j2 ARCH_TYPE= OSDIR=linux_arm_64 ghidra_opt`, pois o pacote incluía somente o executável Linux x86_64. Não foram alterados registros globais dos clientes REA nem os binários Windows.

| Driver | SHA256 original | Funções locais não thunk recuperadas |
|---|---|---|
| `surfacecamfrontsensor8380.sys` | `80a8e4a1ef8f0dacfbc2e8c6919cb269993057ffd3133c2ef7016ff742e46f03` | 133/133; 11160 linhas de pseudocódigo |
| `surfacecamrearsensor8380.sys` | `b7d7a278c5e7b92ebf35f870a7e06cbad670ffb35bfaf40106e27b09bf33fabb` | 166/166; 13292 linhas de pseudocódigo |
| `qccammipicsi8380.sys` | `033f5b1431ad4c76a12ac3b7f0a5be42e460a03bcff40d249511b3034786d407` | 139/139 |
| `qccamisp8380.sys` | `64463b4d78894fdeee01ce87b51e3153662243e3fdf16f87596579b58617c21c` | 494/494 |
| `qccamplatform8380.sys` | `836714ec41f92f45af363d7bf3c9b9cfc2cccdbd19a1c57f355b471068648049` | 219/219 |

A contagem cobre as funções que **Ghidra identificou**, excluindo imports e thunks; não comprova recuperação perfeita de limites/tipos ou compreensão de cada rotina. PDB original não foi carregado. A recuperação em lote usa a sessão MCP persistente do REA; manifestos privados distinguem sucesso, falhas, hashes e IDs de evidência.

## Container dos módulos de sensor

Os arquivos `com.surface.sensormodule.*.bin` usam `QTI Chromatix Header`, campos de versão 3/1 e identificam Parameter Parser V3.4.0. O novo `scripts/decode-camera-module.py` verifica tamanho, CRC32, seções, símbolos e limites; confere referências na interpretação candidata; recusa sobrescrita e publica JSON privado atomicamente. Formatos desconhecidos são recusados ou mantidos como dados sem interpretação, conforme o nível afetado.

Estrutura observada nos oito módulos disponíveis:

- Diretório de seções em offset declarado no cabeçalho; cada entrada tem 12 bytes: ID, offset e tamanho.
- Seção 0: descritores de 56 bytes, com ID, nome de 32 bytes, três campos ainda sem semântica estabelecida, offset e comprimento relativos à seção de dados.
- Seção 1: payloads dos símbolos, inclusive campos opcionais de comprimento zero e payloads compartilhados. Esses compartilhamentos não são erro de sobreposição de seções.
- O último uint32 é CRC32 do prefixo completo. Todos os oito arquivos passaram na verificação.
- `regSetting` observado: registros de 40 bytes com endereço e referências a `slaveAddr`, vetor `registerData` e `delayUs`; marcadores, comprimentos e nomes referenciados são conferidos. Tipos e operações continuam preservados como enums RAW. `slaveAddr` opcional tem 16 bits; dados e delays usam palavras de 32 bits neste layout.
- `powerSetting`: triplas numéricas de 12 bytes preservadas. Ainda não atribuir nomes/voltagens/unidades aos enums apenas por aparência.

A reconstrução de cada payload foi confrontada diretamente com os bytes nos offsets originais e com seu SHA256. Limites de entrada, seções, símbolos, soma de payloads e orçamento agregado de referências expandidas limitam memória/JSON mesmo com dados compartilhados. Erros no esquema candidato são registrados localmente, mantendo os símbolos validados; corrupção estrutural do container continua recusada. Sete testes do decoder cobrem dados válidos, CRC/tamanho corrompidos, referências/contagens inválidas, limites, opcionais vazios, compartilhamento, formatos desconhecidos, arquivos especiais e preservação de destino existente. Os oito módulos reais foram novamente conferidos com a versão final: zero erros de interpretação candidata.

| Sensor desta máquina | SHA256 do módulo | Símbolos | Registros candidatos, todos os conjuntos |
|---|---|---:|---:|
| IMX681 | `f7dd81be64153fd3f0da8e6288ee1b9906b7bf51b773a98496934d76dc96a45c` | 3035 | 915 |
| OV13858 | `f8f60e79b77bd3d5896cb04167ee428455e1a241f1ff9e50abee6b4dacfe6b14` | 2117 | 632 |
| VD55G0 MSHW0492 | `e574db7eb28231d3fa4f5eee5c1861919125d8ec7a753fc7a0708606e1f1a794` | 1956 | 613 |

Outras variantes foram decodificadas para validar o formato, sem selecioná-las para este aparelho. A identidade Windows SONY0681/MSHW0490 e OVTID858/MSHW0491 já foi verificada na enumeração nativa anterior.

## Confronto dos sensores com o candidato Linux

Base de câmera: `turbineBMW/surface-pro-11-linux` revisão `15e590c3c3298dd75a0b79256efa815c15dc0897`, patch SHA256 `16cdb32c732dde20f088c27bd1b83b269e631999c76edf1045126ff220ed3010`, sobre Linux `548e7bcd0c5460ddcbca9600cea603ebeebf4da7`.

**Frontal:** as 364 duplas endereço/valor de `imx681_global_init_table` coincidem, em ordem, com o símbolo Windows 1859. As 68 duplas de `imx681_mode_3840x2640` coincidem com o símbolo 38. A comparação é de duplas, não uma afirmação de equivalência de todo protocolo, delays, alimentação ou efeitos físicos. Não foram copiados payloads Windows para o driver: o candidato já continha essas duplas como implementação aberta de observações do autor.

**Traseira:** o modo específico `mode_4076x2806_regs`, concatenado após `mipi_data_rate_1186mbps`, tem 207 duplas. Contra o conjunto Windows 39, 206 coincidem; a diferença é `0x3813`: candidato `0x15`, Windows `0x14`. Outros modos Windows diferem em crop/dimensões. A diferença não foi alterada automaticamente: o driver declara Bayer GRBG, e deslocamento de linha pode afetar a fase. Faltam teste de cor e confirmação de intenção do candidato. Não declarar tabelas traseiras idênticas.

Há outra inconsistência verificável: o driver oferece 592800000 Hz para esse modo, mas o endpoint DT lista somente 540/270 MHz. `patches/kernel/0004-sp11-camera-rear-endpoint.patch` acrescenta a frequência já usada pelo driver. Isso corrige a descrição; não foi demonstrado que a inconsistência cause a falha física relatada.

## Alimentação e processamento: o que o código realmente mostra

O fluxo frontal decompilado em `0x140005270` chama ativação do dispositivo, inicialização I2C, abertura/alimentação MIPI/CSI, inicialização do sensor e configuração de modo, com verificações de estado/erro. Evidência REA `ev_ba8feb52137ed46c78029d7bab43105bdd23ecb1fcad79c4711ccb511062b0a6`. O chamado `0x14000b470` passa por WDF/idle; não contém sozinho toda a sequência elétrica. Os helpers `0x140002bd8`/`0x140002d70` obtêm a interface de enumeração de recursos e leem a configuração registrada. Chamadas indiretas protegidas por CFG ainda precisam de resolução para comprovar a execução de cada recurso.

O módulo traseiro genérico contém 24000000 na tripla de clock, enquanto o recurso específico `CAMS_RES_MSHW0491.bin` contém `cam_cc_mclk1_clk` e 19200000, coerente com o DT e o driver candidatos. Isso demonstra por que não se deve transpor o módulo genérico sobre o mapa de placa sem seguir seus consumidores. Os [recursos específicos](CAMERA_RESOURCE_FINDINGS.md) continuam sendo a evidência para a seleção da placa.

O helper `0x140004080` multiplica o argumento por -10000 antes de `KeDelayExecutionThread`: com a unidade de 100 ns documentada pela Microsoft, o argumento corresponde a milissegundos. O processador de wait `0x140007948` diferencia caminho de stall e caminho de espera por software; o stall usa `KeStallExecutionProcessor`, cujo argumento é microsegundos. Isso não estabelece automaticamente a unidade das triplas `powerSetting`. Fontes: [KeDelayExecutionThread](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kedelayexecutionthread), [KeStallExecutionProcessor](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kestallexecutionprocessor).

## C-PHY: verificação com os bytes do driver Windows

A rotina CSI decompilada `0x140001c70` distingue C-PHY e D-PHY e consulta uma tabela para o settle de C-PHY. O REA leu 208 bytes em `0x14000dab0`, mapeados ao offset de arquivo 52400; o resultado foi conferido contra os bytes originais. Evidências `ev_1abd7b4250fcecefb35c1728845ca6c6b4c4a19b9cac2e73003e8bc311d862c4` e `ev_b6f3cc332bd7f63da648b14803e9cca47400af0463cd8d9b3ef78cc2179f1640`.

Para **2406 Msym/s declarados pelo candidato**, a busca pela primeira faixa estritamente superior seleciona limiar 2500 e settle 34 (`0x22`). O cabeçalho Linux `x1e80100-cphy-observed.h` contém esse valor em 0x020c/0x060c/0x0a0c. Essa correspondência é estática e condicional à taxa declarada; não foi capturada a taxa realmente enviada pelo Windows desta unidade nem medido o sinal físico.

## ISP e a documentação Qualcomm

A [página indicada pelo usuário](https://docs.qualcomm.com/doc/80-70015-17/topic/camera_overview.html), recuperada também em seu [Markdown público](https://docs.qualcomm.com/bundle/publicresource/80-70015-17/topics/camera_overview.md), diferencia o Camera Core proprietário/downstream do CAMSS V4L2 upstream. Ela não comprova sozinha suporte ao X1P, mas confirma que esses caminhos não devem ser confundidos. O candidato Linux já contém CAMSS e captura RAW; não demonstramos que implementar todo IPC de CAMERA_ICP seja pré-requisito para essas capturas.

A afirmação anterior de que seriam obrigatórias 30000–50000 linhas de driver, ou de que bastaria aguardar um ISP genérico, não tinha evidência suficiente e não orienta este trabalho. O firmware local `CAMERA_ICP_AAAAAA.elf` foi identificado como ELF32 Xtensa, com debug info; isso também não define sozinho o caminho que deve ser usado no Linux.

## Próximas verificações necessárias

1. Identificar kernel/DTB realmente inicializados e obter media graph, binding I2C e erros de probe no Fedora físico.
2. Compilar/stagear kernel candidato e libcamera com suporte IMX681, preservando a instalação de trabalho. O rootfs contém libcamera/IPA 0.7.0-1.fc44; `libcamera-tools` e tuning IMX681 estão ausentes. As bibliotecas examinadas não contêm o literal imx681.
3. Capturar frames RAW e saída processada da frontal e traseira, com identidade, dimensões, formatos, hashes distintos, estado do indicador e journal pós-captura. Faltam esses resultados físicos.
4. Se houver falha, seguir o ponto comprovado (probe/alimentação/CSI/IFE/DMA/userspace), ampliando a REA necessária. Não usar o número de linhas como limite de esforço ou critério de conclusão.
