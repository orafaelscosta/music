"""Testes para as rotas API."""

import pytest


# ============================================================
# Testes de Health Check
# ============================================================
class TestHealthCheck:
    """Testes para o endpoint de health check."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        """Health check retorna status ok."""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


# ============================================================
# Testes de Projects CRUD
# ============================================================
class TestProjectsAPI:
    """Testes para rotas de projetos."""

    @pytest.mark.asyncio
    async def test_create_project(self, client):
        """Cria um projeto com sucesso."""
        response = await client.post(
            "/api/projects",
            json={"name": "Teste", "description": "Projeto de teste", "language": "it"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Teste"
        assert data["language"] == "it"
        assert data["status"] == "created"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_project_minimal(self, client):
        """Cria projeto apenas com nome."""
        response = await client.post(
            "/api/projects",
            json={"name": "Minimal"},
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Minimal"

    @pytest.mark.asyncio
    async def test_list_projects(self, client):
        """Lista projetos retorna lista."""
        # Criar um projeto
        await client.post("/api/projects", json={"name": "P1"})

        response = await client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_project(self, client):
        """Busca projeto por ID."""
        create_resp = await client.post("/api/projects", json={"name": "Get Test"})
        project_id = create_resp.json()["id"]

        response = await client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client):
        """Busca projeto inexistente retorna 404."""
        response = await client.get("/api/projects/inexistente")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_project(self, client):
        """Atualiza projeto com sucesso."""
        create_resp = await client.post("/api/projects", json={"name": "Original"})
        project_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/projects/{project_id}",
            json={"name": "Atualizado", "lyrics": "La la la"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Atualizado"
        assert response.json()["lyrics"] == "La la la"

    @pytest.mark.asyncio
    async def test_delete_project(self, client):
        """Deleta projeto com sucesso."""
        create_resp = await client.post("/api/projects", json={"name": "Delete Me"})
        project_id = create_resp.json()["id"]

        response = await client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 204

        # Confirmar que não existe mais
        get_resp = await client.get(f"/api/projects/{project_id}")
        assert get_resp.status_code == 404


# ============================================================
# Testes de Voices/Engines
# ============================================================
class TestVoicesAPI:
    """Testes para rotas de vozes e engines."""

    @pytest.mark.asyncio
    async def test_list_voices(self, client):
        """Lista voicebanks retorna dict."""
        response = await client.get("/api/voices")
        assert response.status_code == 200
        data = response.json()
        assert "diffsinger" in data
        assert "rvc" in data

    @pytest.mark.asyncio
    async def test_list_engines(self, client):
        """Lista engines retorna info de cada engine."""
        response = await client.get("/api/voices/engines")
        assert response.status_code == 200
        data = response.json()
        assert "diffsinger" in data
        assert "acestep" in data
        assert "applio" in data

    @pytest.mark.asyncio
    async def test_test_engine_pedalboard(self, client):
        """Testa engine pedalboard."""
        response = await client.post("/api/voices/engines/pedalboard/test")
        assert response.status_code == 200
        data = response.json()
        assert data["engine"] == "pedalboard"
        assert isinstance(data["available"], bool)


# ============================================================
# Testes de Pipeline Status
# ============================================================
class TestPipelineAPI:
    """Testes para rotas do pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_status(self, client):
        """Status do pipeline retorna informações corretas."""
        create_resp = await client.post("/api/projects", json={"name": "Pipeline Test"})
        project_id = create_resp.json()["id"]

        response = await client.get(f"/api/pipeline/{project_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "steps" in data

    @pytest.mark.asyncio
    async def test_pipeline_status_not_found(self, client):
        """Pipeline status para projeto inexistente retorna 404."""
        response = await client.get("/api/pipeline/inexistente/status")
        assert response.status_code == 404


# ============================================================
# Testes de Mix Presets
# ============================================================
class TestMixAPI:
    """Testes para rotas de mixagem."""

    @pytest.mark.asyncio
    async def test_list_presets(self, client):
        """Lista presets de mixagem."""
        create_resp = await client.post("/api/projects", json={"name": "Mix Test"})
        project_id = create_resp.json()["id"]

        response = await client.get(f"/api/mix/{project_id}/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert len(data["presets"]) == 5

    @pytest.mark.asyncio
    async def test_mix_status(self, client):
        """Status da mixagem retorna info correta."""
        create_resp = await client.post("/api/projects", json={"name": "Mix Status"})
        project_id = create_resp.json()["id"]

        response = await client.get(f"/api/mix/{project_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert "has_vocal" in data
        assert "has_instrumental" in data
        assert "has_mix" in data

    @pytest.mark.asyncio
    async def test_render_mix_no_vocal(self, client):
        """Renderizar mix sem vocal retorna erro."""
        create_resp = await client.post("/api/projects", json={"name": "No Vocal"})
        project_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/mix/{project_id}/render",
            json={
                "vocal_gain_db": 0,
                "instrumental_gain_db": -3,
                "eq_low_gain_db": 0,
                "eq_mid_gain_db": 2,
                "eq_high_gain_db": 1,
                "compressor_threshold_db": -18,
                "compressor_ratio": 3,
                "reverb_room_size": 0.3,
                "reverb_wet_level": 0.15,
                "limiter_threshold_db": -1,
            },
        )
        assert response.status_code == 400


# ============================================================
# Testes de Refinement
# ============================================================
class TestRefinementAPI:
    """Testes para rotas de refinamento."""

    @pytest.mark.asyncio
    async def test_list_models(self, client):
        """Lista modelos RVC disponíveis."""
        create_resp = await client.post("/api/projects", json={"name": "Refine Test"})
        project_id = create_resp.json()["id"]

        response = await client.get(f"/api/refinement/{project_id}/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_compare_no_files(self, client):
        """Comparação A/B sem arquivos retorna null."""
        create_resp = await client.post("/api/projects", json={"name": "Compare Test"})
        project_id = create_resp.json()["id"]

        response = await client.get(f"/api/refinement/{project_id}/compare")
        assert response.status_code == 200
        data = response.json()
        assert data["before"] is None
        assert data["after"] is None


# ============================================================
# Testes de Synthesis Status
# ============================================================
class TestSynthesisAPI:
    """Testes para rotas de síntese."""

    @pytest.mark.asyncio
    async def test_synthesis_status(self, client):
        """Status da síntese retorna info correta."""
        create_resp = await client.post("/api/projects", json={"name": "Synth Test"})
        project_id = create_resp.json()["id"]

        response = await client.get(f"/api/synthesis/{project_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        assert "files" in data
        assert "engine" in data
