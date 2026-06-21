# ag-05 — Apache Guacamole browser access to HEADLESS-1

Test Apache Guacamole as a proxy to HEADLESS-1 (via wayvnc). Guacamole provides a rich web UI with audio, file management, clipboard, and multi-protocol support.

## Inherits
- [../e009-xiaomi-display/AGENTS.md](../e009-xiaomi-display/AGENTS.md)
- [../ag-03/AGENTS.md](../ag-03/AGENTS.md) (virtual display setup, wayvnc)

## Architecture

```
Browser → HTTP:8085 → Guacamole (Tomcat) → guacd:4822 → wayvnc:5900 → HEADLESS-1
              │
              └── Audio: separate ffmpeg endpoint (same as ag-03)
```

## Docker test

```bash
# Pull images
docker pull guacamole/guacd:latest
docker pull guacamole/guacamole:latest

# Start guacd (the proxy daemon)
docker run --rm -d --name guacd guacamole/guacd:latest

# Start Guacamole web app, connected to guacd + our wayvnc
docker run --rm -d --name guacamole --link guacd:guacd \
  -e GUACD_HOSTNAME=guacd \
  -e GUACD_PORT=4822 \
  -e VNC_HOSTNAME=192.168.0.93 \
  -e VNC_PORT=5900 \
  -p 8085:8080 \
  guacamole/guacamole:latest
```

Then open `http://192.168.0.93:8085/guacamole` in the browser.

### Connection config
- Protocol: VNC
- Hostname: 192.168.0.93
- Port: 5900
- No authentication required (wayvnc has no password)

## Comparison

| Feature | noVNC (ag-03) | Apache Guacamole |
|---------|---------------|-------------------|
| Setup | One Python script | Docker: guacd + Tomcat |
| Audio | External ffmpeg | Built-in (via VNC audio extension) |
| File transfer | No | Yes (download/upload) |
| Clipboard | Text only | Bidirectional |
| Terminal | No | Built-in SSH/Telnet |
| Multi-protocol | VNC only | VNC, RDP, SSH, Telnet, Kubernetes |
| UI polish | Basic | Professional, themable |
| Scaling | Manual CSS | Built-in |
| Authentication | No | Yes (JDBC/LDAP/SSO) |
| Resource usage | Low (single Python) | High (Java + Tomcat) |

## Ports

| Port | Service |
|------|---------|
| 5900 | wayvnc (HEADLESS-1) |
| 4822 | guacd (internal Docker) |
| 8085 | Guacamole web UI |

## Findings

Guacamole (oznu/guacamole Docker image) connects successfully to wayvnc:5900.

- Web UI at http://IP:8086 (guacadmin/guacadmin)
- Connection configured via direct PostgreSQL INSERT (no REST API needed)
- Parameters: hostname=192.168.0.93, port=5900, color-depth=24, cursor=local

Key observations:
- Guacamole renders HEADLESS-1 in a polished web UI
- Latency is slightly higher than noVNC (due to Java/Tomcat stack)
- Audio is not yet tested (needs separate configuration)
- The oznu/guacamole image bundles PostgreSQL + Tomcat + guacd in one container
- API is unstable (returns 500 errors), database injection works reliably

### Auto-configure connection via SQL

```bash
# Start container
docker run --rm -d -p 8086:8080 --name guac -e VNC_SERVER=192.168.0.93:5900 oznu/guacamole:latest

# Add connection to PostgreSQL
docker exec guac psql -U guacamole -d guacamole_db -c "
INSERT INTO guacamole_connection (connection_name, protocol) VALUES ('HEADLESS-1', 'vnc');
INSERT INTO guacamole_connection_parameter (connection_id, parameter_name, parameter_value)
  SELECT currval('guacamole_connection_connection_id_seq'), 'hostname', '192.168.0.93'
  UNION SELECT currval('guacamole_connection_connection_id_seq'), 'port', '5900'
  UNION SELECT currval('guacamole_connection_connection_id_seq'), 'color-depth', '24'
  UNION SELECT currval('guacamole_connection_connection_id_seq'), 'cursor', 'local';
INSERT INTO guacamole_connection_permission (entity_id, connection_id, permission)
  VALUES (1, (SELECT connection_id FROM guacamole_connection WHERE connection_name='HEADLESS-1'), 'READ');
"
