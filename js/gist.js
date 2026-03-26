// gist.js - Gist 读写封装
// 依赖：需要在调用前设置 window.GITHUB_TOKEN 和 window.GIST_ID

class GistManager {
    constructor() {
        this.token = localStorage.getItem('github_token');
        this.gistId = localStorage.getItem('gist_id');
    }

    // 更新 token 和 gistId（保存到 localStorage）
    setCredentials(token, gistId) {
        this.token = token;
        this.gistId = gistId;
        if (token) localStorage.setItem('github_token', token);
        if (gistId) localStorage.setItem('gist_id', gistId);
    }

    // 清除凭证
    clearCredentials() {
        this.token = null;
        this.gistId = null;
        localStorage.removeItem('github_token');
        localStorage.removeItem('gist_id');
    }

    // 检查是否已配置
    isConfigured() {
        return !!(this.token && this.gistId);
    }

    // 获取 Gist 内容（返回 JSON 对象）
    async getConfig() {
        if (!this.isConfigured()) {
            throw new Error('未配置 GitHub Token 或 Gist ID');
        }

        const url = `https://api.github.com/gists/${this.gistId}`;
        const response = await fetch(url, {
            headers: {
                'Authorization': `token ${this.token}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(`获取 Gist 失败: ${error.message || response.statusText}`);
        }

        const gist = await response.json();
        const files = gist.files;
        
        // 查找 gold_alert_config.json 文件
        const configFile = files['gold_alert_config.json'];
        if (!configFile) {
            throw new Error('Gist 中未找到 gold_alert_config.json 文件');
        }

        try {
            return JSON.parse(configFile.content);
        } catch (e) {
            throw new Error('配置文件格式错误，不是有效的 JSON');
        }
    }

    // 更新 Gist 内容
    async updateConfig(data) {
        if (!this.isConfigured()) {
            throw new Error('未配置 GitHub Token 或 Gist ID');
        }

        const url = `https://api.github.com/gists/${this.gistId}`;
        const payload = {
            files: {
                'gold_alert_config.json': {
                    content: JSON.stringify(data, null, 2)
                }
            }
        };

        const response = await fetch(url, {
            method: 'PATCH',
            headers: {
                'Authorization': `token ${this.token}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(`更新 Gist 失败: ${error.message || response.statusText}`);
        }

        return await response.json();
    }

    // 测试连接（仅读取，验证凭证是否正确）
    async testConnection() {
        try {
            await this.getConfig();
            return { success: true, message: '连接成功，配置文件可正常读取' };
        } catch (error) {
            return { success: false, message: error.message };
        }
    }
}

// 创建全局实例
window.gistManager = new GistManager();