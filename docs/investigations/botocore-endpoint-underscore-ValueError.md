# Investigação: Botocore `ValueError: Invalid endpoint` com Underscores no Hostname

## 1. Contexto e Sintoma

Ao configurar um endpoint S3 apontando para um serviço Docker Compose cujos nomes contêm underscores (`_`), como `http://garage_garage:3900`, a inicialização do `s3fs` / `botocore` falha com a seguinte exceção:

```
ValueError: Invalid endpoint: http://garage_garage:3900
```

---

## 2. Análise da Causa Raiz

1. **Validação Estrita de RFC em `botocore.endpoint.is_valid_endpoint_url`**:
   - O `botocore` (biblioteca subjacente usada pelo `s3fs` e `aiobotocore`) valida URLs de endpoint utilizando uma expressão regular estrita para o hostname baseada em padrões DNS oficiais (RFC 952 / RFC 1123).
   - O caractere underscore (`_`) **não** é permitido por essa regex do botocore.
   - Em redes Docker Compose, é comum nomear serviços utilizando underscores (ex: `garage_garage`), tornando essa validação restritiva incompatível com o uso direto de nomes de serviços Docker contendo `_`.

---

## 3. Levantamento: Existe algum parâmetro de configuração nativo no Botocore / S3FS?

Após análise do código-fonte e documentação do `botocore`, `aiobotocore` e `s3fs`:

- **Não existe** nenhuma flag, parâmetro de configuração, variável de ambiente ou opção em `client_kwargs` / `config_kwargs` no Botocore que desabilite a validação estrita de hostnames (`is_valid_endpoint_url`) ou permita o caractere underscore (`_`).
- A validação ocorre estritamente na camada de inicialização do endpoint do botocore antes de qualquer requisição HTTP ser despachada.

---

## 4. Alternativas e Formas de Contorno (Workarounds) Recomendadas

Como o Botocore rejeita nativamente hostnames com underscores (`_`), as seguintes abordagens podem ser adotadas na infraestrutura ou configuração sem alterar o código da aplicação:

### 4.1. Renomear o Serviço no Docker Compose (Recomendado)
Substituir o underscore (`_`) por hífen (`-`) no nome do serviço no `docker-compose.yml`:
- **De**: `garage_garage`
- **Para**: `garage-garage`
- **Endpoint resultante**: `http://garage-garage:3900`
*(O DNS do Docker resolve hífens perfeitamente, e hífens são totalmente compatíveis com a RFC de hostnames e com a validação do Botocore).*

### 4.2. Utilizar Aliases de Rede no Docker Compose
Manter o nome do serviço ou adicionar um alias sem underscores na rede Docker:
```yaml
services:
  garage_garage:
    image: ...
    networks:
      app-net:
        aliases:
          - garage
```
- **Endpoint resultante**: `http://garage:3900`

### 4.3. Utilizar Endereço IP Fixo ou `localhost` / `127.0.0.1`
Caso o serviço S3 seja acessível via IP interno da bridge do Docker ou porta mapeada no host:
- **Exemplo**: `http://172.17.0.2:3900` ou `http://host.docker.internal:3900`
*(Endereços IP passam na validação de formato do botocore).*
