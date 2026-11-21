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
