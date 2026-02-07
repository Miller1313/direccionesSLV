// bot-server/update-github.js
require('dotenv').config();
const fs = require('fs').promises;
const path = require('path');
const axios = require('axios');

async function updateGitHub() {
    try {
        const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
        const GITHUB_USERNAME = process.env.GITHUB_USERNAME;
        const GITHUB_REPO = process.env.GITHUB_REPO;

        if (!GITHUB_TOKEN || !GITHUB_USERNAME || !GITHUB_REPO) {
            console.error('❌ Variables de GitHub no configuradas');
            return;
        }

        // Leer archivo JSON
        const filePath = path.join(__dirname, '../honduras-database.json');
        const data = await fs.readFile(filePath, 'utf8');
        const jsonData = JSON.parse(data);
        
        const fileContent = Buffer.from(data).toString('base64');

        // Obtener SHA del archivo actual
        const getResponse = await axios.get(
            `https://api.github.com/repos/${GITHUB_USERNAME}/${GITHUB_REPO}/contents/honduras-database.json`,
            {
                headers: {
                    'Authorization': `token ${GITHUB_TOKEN}`,
                    'Accept': 'application/vnd.github.v3+json'
                }
            }
        );

        const sha = getResponse.data.sha;

        // Actualizar el archivo
        const updateResponse = await axios.put(
            `https://api.github.com/repos/${GITHUB_USERNAME}/${GITHUB_REPO}/contents/honduras-database.json`,
            {
                message: `🤖 Actualización automática - ${new Date().toLocaleString()}`,
                content: fileContent,
                sha: sha,
                committer: {
                    name: 'Honduras Bot',
                    email: 'bot@honduras.com'
                }
            },
            {
                headers: {
                    'Authorization': `token ${GITHUB_TOKEN}`,
                    'Accept': 'application/vnd.github.v3+json'
                }
            }
        );

        console.log('✅ GitHub actualizado exitosamente');
        console.log(`🔗 ${updateResponse.data.commit.html_url}`);

    } catch (error) {
        console.error('❌ Error actualizando GitHub:', error.message);
    }
}

// Ejecutar si se llama directamente
if (require.main === module) {
    updateGitHub();
}

module.exports = { updateGitHub };