#!/bin/sh

COUCHDB_URL=${1:-"http://admin:admin@localhost:5984"}

echo "Checking CouchDB cluster setup status at ${COUCHDB_URL}..."
STATUS=$(curl -s "${COUCHDB_URL}/_cluster_setup/status")

if echo "$STATUS" | grep -q 'single_node_enabled\|cluster_enabled'; then
  echo "CouchDB is already configured: $STATUS"
else
  echo "Setting up CouchDB as a single node..."
  
  CREDS=$(echo "$COUCHDB_URL" | sed -n 's|.*://\([^:]*\):\([^@]*\)@.*|\1 \2|p')
  USER=$(echo $CREDS | awk '{print $1}')
  PASS=$(echo $CREDS | awk '{print $2}')
  
  USER=${USER:-admin}
  PASS=${PASS:-admin}

  curl -X POST "${COUCHDB_URL}/_cluster_setup" \
    -H "Content-Type: application/json" \
    -d "{
      \"action\": \"enable_single_node\",
      \"username\": \"${USER}\",
      \"password\": \"${PASS}\",
      \"bind_address\": \"0.0.0.0\",
      \"port\": 5984
    }"
  echo ""
fi
