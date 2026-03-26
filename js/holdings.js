// holdings.js - 持仓计算和业务逻辑

class HoldingsManager {
    constructor() {
        this.config = null;  // 缓存当前配置
    }

    // 从 Gist 加载配置
    async loadConfig() {
        if (!window.gistManager.isConfigured()) {
            throw new Error('请先在配置页设置 GitHub Token 和 Gist ID');
        }
        this.config = await window.gistManager.getConfig();
        
        // 确保必要字段存在
        if (!this.config.holdings) this.config.holdings = [];
        if (!this.config.weighted_avg_cost) this.config.weighted_avg_cost = 0;
        if (!this.config.fixed_threshold) this.config.fixed_threshold = 1000;
        if (!this.config.webhook_url) this.config.webhook_url = '';
        if (!this.config.last_alert) this.config.last_alert = { price: 0, datetime: '' };
        if (!this.config.last_price) this.config.last_price = { price: 0, source: '', time: '' };
        
        return this.config;
    }

    // 保存配置到 Gist
    async saveConfig() {
        if (!this.config) {
            throw new Error('没有加载配置');
        }
        await window.gistManager.updateConfig(this.config);
    }

    // 计算加权平均成本
    calculateWeightedAvg() {
        if (!this.config.holdings || this.config.holdings.length === 0) {
            return 0;
        }
        let totalAmount = 0;
        let totalGrams = 0;
        for (const h of this.config.holdings) {
            totalAmount += h.amount;
            totalGrams += h.grams;
        }
        return totalGrams > 0 ? totalAmount / totalGrams : 0;
    }

    // 更新加权平均成本并保存
    async updateWeightedAvg() {
        this.config.weighted_avg_cost = this.calculateWeightedAvg();
        await this.saveConfig();
        return this.config.weighted_avg_cost;
    }

    // 添加持仓记录
    async addHolding(amount, price, date) {
        if (!amount || amount <= 0) throw new Error('买入金额必须大于0');
        if (!price || price <= 0) throw new Error('成交金价必须大于0');
        
        const grams = amount / price;
        // 保留4位小数
        const gramsRounded = Math.round(grams * 10000) / 10000;
        
        const newHolding = {
            amount: parseFloat(amount),
            price: parseFloat(price),
            grams: gramsRounded,
            date: date || this.getYesterdayDate()
        };
        
        this.config.holdings.push(newHolding);
        await this.updateWeightedAvg();
        return newHolding;
    }

    // 删除持仓记录
    async deleteHolding(index) {
        if (index < 0 || index >= this.config.holdings.length) {
            throw new Error('无效的索引');
        }
        this.config.holdings.splice(index, 1);
        await this.updateWeightedAvg();
    }

    // 更新持仓记录
    async updateHolding(index, amount, price, date) {
        if (index < 0 || index >= this.config.holdings.length) {
            throw new Error('无效的索引');
        }
        if (!amount || amount <= 0) throw new Error('买入金额必须大于0');
        if (!price || price <= 0) throw new Error('成交金价必须大于0');
        
        const grams = amount / price;
        const gramsRounded = Math.round(grams * 10000) / 10000;
        
        this.config.holdings[index] = {
            amount: parseFloat(amount),
            price: parseFloat(price),
            grams: gramsRounded,
            date: date || this.getYesterdayDate()
        };
        
        await this.updateWeightedAvg();
    }

    // 获取昨天的日期（YYYY-MM-DD）
    getYesterdayDate() {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        return yesterday.toISOString().split('T')[0];
    }

    // 获取总持仓克数
    getTotalGrams() {
        if (!this.config.holdings || this.config.holdings.length === 0) return 0;
        return this.config.holdings.reduce((sum, h) => sum + h.grams, 0);
    }

    // 获取总持仓金额
    getTotalAmount() {
        if (!this.config.holdings || this.config.holdings.length === 0) return 0;
        return this.config.holdings.reduce((sum, h) => sum + h.amount, 0);
    }

    // 更新固定阈值
    async updateFixedThreshold(value) {
        this.config.fixed_threshold = parseFloat(value);
        await this.saveConfig();
    }

    // 更新 Webhook URL
    async updateWebhookUrl(url) {
        this.config.webhook_url = url;
        await this.saveConfig();
    }

    // 导出数据
    exportData() {
        return JSON.stringify(this.config, null, 2);
    }

    // 导入数据（替换全部）
    async importData(jsonString) {
        try {
            const newConfig = JSON.parse(jsonString);
            // 验证必要字段
            if (!newConfig.hasOwnProperty('holdings')) {
                throw new Error('导入的数据缺少 holdings 字段');
            }
            this.config = newConfig;
            await this.saveConfig();
            return true;
        } catch (e) {
            throw new Error(`导入失败: ${e.message}`);
        }
    }
}

window.holdingsManager = new HoldingsManager();