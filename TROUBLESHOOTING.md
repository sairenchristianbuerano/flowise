# Troubleshooting Docker Startup Issues

## Problem: "Read-only file system" or "FileNotFoundError" on startup

If you see errors like:
```
OSError: [Errno 30] Read-only file system: '/app'
FileNotFoundError: [Errno 2] No such file or directory: '/app/data/components'
```

### Solution Steps:

1. **Stop and remove all containers and volumes:**
   ```bash
   cd flowise
   docker-compose down -v
   ```

2. **Clean up old images:**
   ```bash
   docker-compose down --rmi all -v
   ```

3. **Rebuild from scratch:**
   ```bash
   docker-compose build --no-cache
   ```

4. **Start services:**
   ```bash
   docker-compose up -d
   ```

5. **Monitor startup logs:**
   ```bash
   docker-compose logs -f
   ```

### Alternative: Check Docker permissions

If the above doesn't work, check Docker permissions:

```bash
# Check if your user is in the docker group
groups

# If not, add yourself (requires logout/login after):
sudo usermod -aG docker $USER
```

### Verify volumes are created properly:

```bash
docker volume ls | grep flowise
```

You should see:
- `flowise_component_data`
- `flowise_index_data`

### If issues persist:

1. Check Docker daemon is running: `docker info`
2. Check disk space: `df -h`
3. Check Docker logs: `journalctl -u docker`
4. Try removing all volumes manually:
   ```bash
   docker volume rm flowise_component_data flowise_index_data
   ```

### Environment file check:

Ensure you have a `.env` file in the `flowise/` directory with:
```bash
ANTHROPIC_API_KEY=your_key_here
```
