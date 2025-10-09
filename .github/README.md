# GitHub Actions Configuration

## Required Secrets

Para que el auto-deploy funcione, necesitas configurar estos secrets en GitHub:

### 1. Ir a GitHub Repository Settings
```
https://github.com/devidbarreiro/diaresis/settings/secrets/actions
```

### 2. Añadir los siguientes secrets:

#### `SERVER_HOST`
```
51.91.166.216
```
O si ya está configurado el DNS:
```
gravity.cc
```

#### `SERVER_USER`
```
ubuntu
```

#### `SSH_PRIVATE_KEY`
La clave privada SSH para conectarse al servidor. 

**Obtener la clave:**
```bash
cat ~/.ssh/id_rsa
```

O generar una nueva clave específica para GitHub Actions:
```bash
ssh-keygen -t ed25519 -C "github-actions@gravity.cc" -f ~/.ssh/github_actions_key
```

Luego añade la clave pública al servidor:
```bash
cat ~/.ssh/github_actions_key.pub >> ~/.ssh/authorized_keys
```

Y copia el contenido de la clave privada a GitHub Secrets:
```bash
cat ~/.ssh/github_actions_key
```

## Cómo funciona

1. **Push a main**: Cada vez que haces push a `main`, se activa el workflow
2. **PR Merge**: Cuando se hace merge de un PR a `main`, también se activa
3. **Deploy automático**: 
   - Se conecta al servidor via SSH
   - Hace `git pull`
   - Reconstruye los contenedores con `docker-compose up -d --build`
   - Verifica que la API responda correctamente

## Testing manual

Puedes probar el workflow manualmente desde:
```
https://github.com/devidbarreiro/diaresis/actions
```

Click en "Run workflow" para ejecutarlo sin hacer push.

