# EIEZ-LANG – Roadmap do Projeto

Este documento apresenta o roadmap oficial do **EIEZ-LANG**, uma linguagem de script quântico minimalista e open-source.  
O projeto é simples por design, mas estruturado para evoluir organicamente com a ajuda da comunidade.

---

## Status Atual (v0.1 – Lançamento Básico Público)

- Sintaxe mínima da DSL implementada  
- Lexer e parser funcionais  
- AST e Representação Intermediária básicas  
- Gerador para OpenQASM 2.0  
- Otimizador falso/determinístico (placeholder seguro)  
- Exemplos e documentação simples  
- Licença MIT  

---

## Metas de Curto Prazo (v0.2 – v0.3)

### 🧩 Melhorias na Sintaxe e Gramática
- Expansão das definições de portas quânticas  
- Suporte a portas customizadas  
- Erros e diagnósticos mais claros  
- Introdução de `include`, variáveis e expressões simples  

### Documentação
- Referência completa da gramática  
- Mais programas exemplo `.eiez`  
- Tutoriais para iniciantes  
- Diagramas do pipeline do compilador  

### Ferramentas
- CLI para compilação (`eiezc`)  
- Estrutura de projeto aprimorada  
- Testes unitários para lexer e parser  
- Preparação para publicação no PyPI  

---

## Metas de Médio Prazo (v0.4 – v0.6)

### Recursos da Linguagem
- Condicionais (`if`, `while`)  
- Registros clássicos + aritmética básica  
- Sistema de macros ou blocos reutilizáveis  

### Melhorias no Compilador
- Passes de otimização reais (mas simples)  
- Transformações na AST  
- Pipeline modularizado  

### Integrações
- Melhor conformidade com OpenQASM 2.0  
- Suporte experimental a OpenQASM 3.0  
- Exportação para formatos alternativos (ex.: IR em JSON)  

---

##  Visão de Longo Prazo (v1.0+)

###  Objetivos Principais
- Especificação estável da linguagem  
- Sistema de plugins para passes customizados  
- Integração com simuladores quânticos  
- REPL interativa (`eiez shell`)  

###  Possibilidades Futuras
- Multi-backend (diversos compiladores/targets)  
- Ferramentas de análise estática  
- Gramática formal em ANTLR ou Lark  
- Extensão para VSCode (syntax highlighting)  

---

##  Itens Guiados pela Comunidade (Sempre Abertos)

- Exemplos e conteúdo educacional  
- Melhorias de documentação  
- Otimizações e desempenho  
- Discussões sobre design da linguagem  

---

##  Resumo

O **EIEZ-LANG** nasce como uma linguagem quântica **simples, segura e open-source**, mas com potencial de crescer para algo muito mais robusto e colaborativo.

Contribuições são sempre bem-vindas.