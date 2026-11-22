---
name: version-bump
description: "Faz o bump automático da versão do projeto com base na análise de Conventional Commits desde a última release. Analisa se o bump deve ser patch, minor ou major, atualiza o pyproject.toml e a aplicação FastAPI, cria o commit de release e a tag Git. Escrito em português do brasil."
---

# Skill de Version Bump (Gerenciamento de Versões e Releases)

Esta skill automatiza o processo de versionamento do projeto `torrent-stats` seguindo Semantic Versioning (SemVer) e Conventional Commits.

## O que a skill faz:
1. **Lê os commits** desde a última release (identificada pelo último commit com padrão `release:` ou pela última tag do Git).
2. **Analisa os Conventional Commits** para julgar o tipo de bump necessário:
   - **Major** (`vX.0.0`): Se houver mudanças incompatíveis (`BREAKING CHANGE` ou `!` no tipo, ex: `feat!:` / `fix!:`).
   - **Minor** (`vx.Y.0`): Se houver novas funcionalidades (`feat:`).
   - **Patch** (`vx.y.Z`): Se houver apenas correções de bugs (`fix:`), refatorações (`refactor:`), documentação (`docs:`), etc., sem alterações que quebram a compatibilidade nem novas features.
   - **Release Candidate (`-rc[n]`):** Suporta geração de release candidate com o sufixo `-rc[n]` (onde `[n]` é um número sequencial começando em 0: `-rc0`, `-rc1`, etc.) ao passar a flag `--rc` ou `--release-candidate`.
3. **Atualiza a versão** no arquivo `pyproject.toml`.
4. **Atualiza a versão da aplicação FastAPI** em `torrent_stats/interfaces/api/main.py` para corresponder à mesma versão.
5. **Cria o commit de release** com a mensagem no padrão `"release: x.x.x"` (ou `x.x.x-rcN`).
6. **Cria a tag no Git** no padrão `vx.x.x` (ou `vx.x.x-rcN`).

## Como Executar

Você pode executar o script de automação localizado em `.agents/skills/version-bump/scripts/bump.py`:

```bash
python3 .agents/skills/version-bump/scripts/bump.py
```

### Opções de Execução:
- **Simulação (Dry-run)**: Para verificar qual seria o bump e a nova versão sem aplicar alterações:
  ```bash
  python3 .agents/skills/version-bump/scripts/bump.py --dry-run
  ```
- **Release Candidate**: Para gerar uma versão release candidate com sufixo `-rc[n]` (ex: `1.1.0-rc0`, `1.1.0-rc1`):
  ```bash
  python3 .agents/skills/version-bump/scripts/bump.py --rc
  ```
  *(Também aceita `--release-candidate`)*

## Regras e Convenções
- **Mensagem de Commit**: `release: x.x.x` (ou `release: x.x.x-rcN`)
- **Tag Git**: `vx.x.x` (ou `vx.x.x-rcN`)
- **Sincronização**: O `pyproject.toml` e o `torrent_stats/interfaces/api/main.py` devem estar sempre sincronizados com a mesma versão da release.
