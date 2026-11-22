# Investigação: S3Storage `TypeError` in `s3fs` (`call_s3` / `commit`)

## 1. Contexto e Sintoma

Durante testes em ambiente de produção utilizando o perfil de armazenamento S3 (`s3`), ao tentar fazer o upload de um arquivo `.torrent`, foi observado o seguinte erro crítico no worker/API:

```
2026-11-21 22:54:07.972 ERROR: ...
  File "/usr/local/lib/python3.15/site-packages/s3fs/core.py", line 2814, in commit
    write_result = self._call_s3("put_object", **kw, **match)
  File "/usr/local/lib/python3.15/site-packages/s3fs/core.py", line 2641, in _call_s3
    return self.fs.call_s3(
        method,
        **kw, **match,
    )
TypeError: S3FileSystem.call_s3() got multiple values for argument keyword argument...
```

---

## 2. Análise da Causa Raiz

1. **Configuração de Perfis via Variáveis de Ambiente**:
   - O `StorageProfilesSettings` lê variáveis no formato `STORAGE_PROFILE_S3_[PARAM]=value` e as armazena no dicionário `profile.config`.
   - Para o perfil S3, parâmetros comuns incluem `bucket`, `key`, `secret`, `endpoint_url`, `target_path_template` e `download_url_template`.

2. **Vazamento do Parâmetro `bucket` para o `s3fs`**:
   - Na implementação anterior de `S3Storage.__init__`, apenas `download_url_template` e `target_path_template` eram removidos de `fs_config` antes de chamar `fsspec.filesystem("s3", **fs_config)`.
   - O parâmetro `bucket` (presente em `profile.config`) permaneceu em `fs_config` e foi repassado diretamente para o construtor `S3FileSystem(bucket="my-bucket", ...)`.
   - O `s3fs` / `botocore` interpreta argumentos desconhecidos ou passa `bucket` em conjunto com o caminho absoluto (ex: `my-bucket/torrents/...`), fazendo com que a operação interna `put_object` receba o argumento `Bucket` (ou `bucket`) múltiplas vezes (`multiple values for argument keyword argument`), resultando em `TypeError`.

---

## 3. Correção Aplicada

1. **Remoção de Parâmetros de Configuração Interna (`bucket`, `target_path_template`, `download_url_template`)**:
   - Em `S3Storage.__init__`, o parâmetro `bucket` agora é removido de `fs_config` junto com os templates, garantindo que o `s3fs` receba apenas os parâmetros de conexão válidos (`key`, `secret`, `endpoint_url`, `region_name`, etc.).
   - O `bucket` continua plenamente disponível em `self.profile.config` para ser interpolado corretamente no `target_path_template` (ex: `{bucket}/torrents/{info_hash}.torrent`).

---

## 4. Prevenção e Testes

- Atualizados os testes unitários em `tests/test_storage.py` para garantir que `bucket` seja tratado corretamente na inicialização e no upload via S3.
- Lançada a versão candidate **`v1.1.0-rc3`** contendo a correção.
