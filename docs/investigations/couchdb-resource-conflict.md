# Investigação: CouchDB Resource Conflict (`Document update conflict`)

## 1. Contexto e Sintoma

Durante a execução da API (FastAPI) com CouchDB, foi observado o seguinte erro crítico ao processar requisições para a rota de torrents (`GET /torrents/{hash}`):

```
couchdb.http.ResourceConflict: ('conflict', 'Document update conflict.')
```

### Stack Trace Completo

```
  File "/app/torrent_stats/interfaces/api/routers/torrents.py", line 47, in get_torrent
    return controller.get_torrent(hash, trackers)
  File "/app/torrent_stats/controllers/torrents.py", line 32, in get_torrent
    total_hits, last_hit_at = self.hit_counter.record_hit(hash)
  File "/app/torrent_stats/services/hit_counter.py", line 47, in record_hit
    self.torrent_repo.save(torrent)
  File "/app/torrent_stats/db/repository.py", line 39, in save
    result = self.client.save_doc(data)
  File "/app/torrent_stats/db/client.py", line 43, in save_doc
    doc_id_saved, rev = db.save(doc)
  File "/usr/local/lib/python3.15/site-packages/couchdb/client.py", line 529, in save
    _, _, data = func(body=doc, **options)
  File "/usr/local/lib/python3.15/site-packages/couchdb/http.py", line 425, in request
    raise ResourceConflict(error)
couchdb.http.ResourceConflict: ('conflict', 'Document update conflict.')
```

---

## 2. Análise do Fluxo de Execução

Ao rastrear o caminho da requisição `GET /torrents/{hash}`, identificou-se o seguinte fluxo no controlador (`TorrentController.get_torrent`):

1. **Contagem de Hits (`HitCounterService.record_hit`)**:
   - Incrementa o contador no Redis (`torrent:hits:{hash}:{hour}`).
   - Calcula o total de hits das últimas 12 horas.
   - Consulta o repositório (`torrent_repo.find_by_info_hash(info_hash)`).
   - **Escrita 1**: Salva o documento no CouchDB com os novos valores de `total_hits` e `last_hit_at`.

2. **Obtenção ou Criação do Metadado (`TorrentMetadataRepository.get_or_create`)**:
   - Logo após o `record_hit`, o controlador chama `get_or_create`.
   - Consulta novamente o documento.
   - **Escrita 2**: Salva o documento no CouchDB novamente atualizando `total_hits` e `last_hit_at`.

3. **Adição de Trackers Padrão / Customizados**:
   - Verifica se há novos trackers informados ou padrão (`target_trackers`).
   - Se houver novos trackers, adiciona-os a `torrent.tracker_stats` e cria tarefas `scrape_stats` pendentes.
   - **Escrita 3**: Salva o documento no CouchDB mais uma vez (`self.torrent_repository.save(torrent)`).

---

## 3. Causas Raiz Identificadas

1. **Múltiplas Escritas Redundantes na Mesma Requisição**:
   - O mesmo documento de metadados do torrent é salvo de 2 a 3 vezes sequencialmente dentro do ciclo de vida de uma única requisição HTTP (`GET /torrents/{hash}`).
   - Isso multiplica as chances de conflito de revisão (`_rev`) no CouchDB, pois cada escrita altera a revisão.

2. **Concorrência entre Requisições (Race Conditions)**:
   - Requisições simultâneas para o mesmo `info_hash` (ex: múltiplos clientes ou scraper/workers acessando a API) leem a mesma revisão antiga do CouchDB e tentam salvar concorrentemente.
   - O CouchDB utiliza Controle de Concorrência Multi-Versão (MVCC), rejeitando atualizações baseadas em revisões desatualizadas com `Document update conflict`.

3. **Falta de Abstração Transacional / Otimização de Persistência**:
   - `HitCounterService` persiste diretamente no CouchDB antes do controller processar o restante das regras de negócio (trackers, tarefas, etc.).
   - Não há um mecanismo de retry automático (optimistic locking retry) ou consolidação das alterações em memória antes de uma única operação de escrita atômica por requisição.

---

## 4. Recomendações para Resolução (Para futura implementação)

- Consolidar as atualizações de metadados do torrent (hits, trackers, etc.) em uma única operação de salvamento por requisição, ou utilizar padrão de retry em caso de `ResourceConflict`.
- Separar ou otimizar `HitCounterService` para não realizar salvamentos redundantes no CouchDB se o controller já vai persistir o estado atualizado do torrent.

---

## 5. Levantamento sobre Operações de Atualização (Update) nos Repositórios e CouchDB

### 5.1. Como o CouchDB lida com Updates?
O CouchDB utiliza armazenamento orientado a documentos JSON e **MVCC (Multi-Version Concurrency Control)** baseado em revisões (`_rev`). O CouchDB nativamente não possui uma operação de "patch" genérica ou update parcial de campos sem passar por document update handlers (funções JS em design docs). 

Portanto, um update em Python/CouchDB padrão consiste em:
1. Buscar o documento atual (obtendo o `_id` e o `_rev` mais recente).
2. Modificar apenas os campos desejados no dicionário/modelo em memória.
3. Salvar o documento com a revisão correspondente.

### 5.2. Revisão dos Repositórios Atuais
Atualmente, a classe `BaseRepository` fornece apenas `get(doc_id)` e `save(instance)`. Não existem métodos específicos de update parcial ou de atualização de campos específicos usando a chave primária. Cada alteração exige carregar o modelo inteiro e dar `save()`, o que sobrescreve o documento inteiro e colide facilmente se o `_rev` mudou.

### 5.3. Métodos Específicos de Update Baseados nas Demandas do Código

Com base nas demandas atuais do sistema, podemos adicionar métodos específicos nos repositórios para atualizar campos pontuais utilizando a chave primária (`info_hash`, `id`, etc.):

1. **`TorrentMetadataRepository.update_hits(info_hash: str, total_hits: int, last_hit_at: str)`**:
   - **Demanda**: `HitCounterService.record_hit` precisa atualizar apenas os hits e a data do último hit do torrent sem precisar reescrever o documento inteiro com dados potencialmente estáticos ou conflitantes de trackers.
   - **Implementação proposta**: Busca o documento pelo `info_hash`, atualiza exclusivamente `total_hits` e `last_hit_at`, preservando `_rev`, e salva.

2. **`TorrentMetadataRepository.add_tracker_stat(info_hash: str, tracker_stat: TrackerStat)`**:
   - **Demanda**: Adicionar novos trackers quando solicitados na rota de torrents.
   - **Implementação proposta**: Busca o documento, verifica se o tracker já existe em `tracker_stats`, faz o `append` caso contrário, e persiste.

3. **`TaskRepository.update_task_status(task_id: str, status: str, ...)`**:
   - **Demanda**: Workers e API atualizam status de tarefas (`pending`, `claimed`, `completed`, `failed`), leases e erros.
   - **Implementação proposta**: Método específico para atualizar status e campos relacionados de uma tarefa por ID.

### 5.4. Isso Resolveria o Problema?
- **Parcialmente para redução de conflitos lógicos**: Ter métodos focados evita carregar e sobrescrever estruturas complexas inteiras desnecessariamente.
- **Não resolve sozinho para concorrência extrema**: Como o CouchDB é baseado em MVCC, se duas requisições tentarem atualizar o mesmo documento no mesmo milissegundo, a segunda falhará com `ResourceConflict` se a revisão tiver mudado.
- **Solução Definitiva Combinada**: Para resolver 100% dos conflitos de concorrência e evitar escritas múltiplas redundantes na mesma requisição, a estratégia ideal combina:
  1. **Métodos de update direcionados** nos repositórios.
  2. **Consolidação em uma única escrita** por requisição HTTP no Controller.
  3. **Mecanismo de Retry com Optimistic Locking** (ex: um decorador ou bloco `try/except` que captura `ResourceConflict`, re-busca a nova revisão e tenta novamente até N vezes) no `CouchDBClient` ou `BaseRepository.save`.
