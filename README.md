AstroControl

Controlador Open-Source de Telescópio AZ/ALT com GOTO e TRACK por Velocidade Angular

Versão: 3.0 Stable
Autor: Bryam S. Sierpinski
Data: 01/2026
Licença: Uso livre (open-source)

1. Visão Geral

O AstroControl é um sistema open-source para controle de telescópios com montagem Altazimutal (AZ/ALT), projetado para operar com motores de passo NEMA 17 controlados por Arduino UNO, oferecendo:

GOTO automático para objetos astronômicos

TRACK contínuo por velocidade angular

Cálculos astronômicos precisos usando Skyfield + efemérides JPL (DE421)

Correção opcional de refração atmosférica

Comunicação serial textual e binária

Interface gráfica em Python (PyQt6)

O projeto foi desenvolvido com foco em precisão, simplicidade de firmware e transparência matemática, evitando abordagens empíricas ou aproximações grosseiras.

2. Arquitetura do Sistema

  Skyfield (Efemérides JPL DE421) -> AstroControl (Python, Cálculo AZ/ALT,Refração, TRACK em °/s) -> USB/Bluetooth -> Arduino UNO (Protocolo texto/binário, Controle de motores) -> Motores de passo (NEMA 17, AZ / ALT)

3. Modelo Astronômico
3.1 Efemérides

  O AstroControl utiliza a biblioteca Skyfield com o arquivo de efemérides DE421, produzido pelo Jet Propulsion Laboratory (NASA).

  Cobertura temporal:

  1900 a 2050

  Objetos suportados:

  Sol

  Lua

  Mercúrio

  Vênus

  Marte

  Júpiter (baricentro)

  Saturno (baricentro)

3.2 Sistema de Coordenadas

  O sistema opera exclusivamente em coordenadas horizontais:

  Azimute (AZ): 0° a 360°

  Altitude (ALT): 0° a 90°

  Conversão:

  RA/DEC → AZ/ALT


  Realizada internamente pelo Skyfield com correções de:

  Precessão

  Nutação

  Aberração

  Paralaxe

  Refração atmosférica (opcional)

3.3 Refração Atmosférica

  Quando ativada, a refração é calculada com base em:

  Temperatura (°C)

  Pressão atmosférica (mbar)

  Esses parâmetros são passados diretamente para o método:

  astrometric.altaz(temperature_C, pressure_mbar)


  Se os dados forem inválidos ou desativados, o cálculo é feito sem correção atmosférica.

4. Lógica de GOTO

  O comando GOTO move o telescópio até uma posição absoluta em AZ/ALT.

4.1 Menor Caminho em Azimute

  Para evitar rotações desnecessárias (>180°), o sistema calcula o menor deslocamento angular:

  delta_az = (az_desejado - az_atual + 180) % 360 - 180


  Isso garante:

  Menor tempo de deslocamento

  Menor desgaste mecânico

  Comportamento previsível

4.2 Verificação de Horizonte

  O sistema bloqueia comandos quando:

  ALT < -0.5°


  Evita apontamentos inválidos abaixo do horizonte geométrico.

5. TRACK por Velocidade Angular
5.1 Conceito

  Diferente de sistemas que enviam GOTO contínuos, o AstroControl implementa tracking verdadeiro, baseado em velocidade angular (°/s).

  A cada ciclo:

  VAZ = (AZ_atual - AZ_anterior) / Δt
  VALT = (ALT_atual - ALT_anterior) / Δt


  Essas velocidades são enviadas ao Arduino, que mantém o movimento contínuo.

5.2 Filtragem

  Para evitar micro-oscilações:

  Variações muito pequenas são ignoradas

  Atualizações ocorrem a cada ~100 ms

6. Comunicação Serial
6.1 Protocolo Textual (ASCII)

  Usado principalmente para GOTO e comandos manuais.

  Comandos:
  GOTO AZ=123.45 ALT=67.89
  TRACK VAZ=0.004321 VALT=0.000123
  ZERO
  STOP

  6.2 Protocolo Binário (TRACK)

  Usado para tracking contínuo com menor latência.

  Frame:
  [0x02][ 'T' ][VAZ][VALT][CHK][0x03]


  VAZ e VALT: int32 (milideg/s, signed, little-endian)

  CHK: checksum simples (soma dos bytes)

  0x02 / 0x03: delimitadores de início/fim

7. Firmware Arduino
7.1 Controle de Motores

  Biblioteca: AccelStepper

  Modo: DRIVER (STEP/DIR)

  Velocidade máxima e aceleração configuráveis

  Conversão:

  steps = graus × STEPS_PER_DEG

7.2 BACKLASH Compensation

  Ao detectar inversão de direção:

  Passos extras são aplicados para compensar folga mecânica

  Parâmetros ajustáveis:

  BACKLASH_AZ_STEPS
  BACKLASH_ALT_STEPS

7.3 Modos de Operação
  Modo	Descrição
  GOTO	Movimento absoluto com aceleração
  TRACK	Velocidade contínua (runSpeed)
  STOP	Parada imediata
  ZERO	Redefine posição como origem

8. Limitações Conhecidas

  Sistema open-loop (sem encoder)

  Não realiza alinhamento automático

  Não implementa plate solving

  Depende da calibração mecânica do usuário

  Essas decisões são intencionais, visando simplicidade e transparência.

9. Público-Alvo

  Astronomia amadora

  Telescópios caseiros

  Dobson motorizado

  Projetos educacionais

  Makers avançados

10. Contribuições

  Contribuições são bem-vindas, especialmente em:

  Documentação

  Testes reais

  Integração com INDI / ASCOM

  Melhorias no protocolo

Este projeto foi criado por curiosidade e aprendizado, mas segue princípios técnicos sólidos.

11. Aviso Final

  Este projeto não é um produto comercial, não possui garantias e deve ser usado com responsabilidade mecânica e elétrica.

  Este produto não pode ser replicado para fins comerciais, apenas projetos open-source e remakes com os devidos créditos protegidos por LEI.