const { inngest } = require("../lib/inngest");
const { execTool } = require("../lib/tools");
const { sendProgress, sendProductCard } = require("../lib/ipc");

const PREP_COST = 1.5;
const SHIPPING_PER_UNIT = 0.5;

/**
 * Calculate profitability metrics for a product.
 */
function calculateProfitability(catalog, pricing, fees, wholesaleCost) {
  const buyBoxPrice = pricing.buy_box_price || 0;
  const totalFees = fees.total_fees || 0;

  // BSR estimation
  let estimatedMonthlySales = 0;
  let demandIndicator = "N/A";
  let sizeTier = "Standard";

  if (catalog.bsr && catalog.bsr_category) {
    const bsrResult = execTool("bsr-estimator.py", [
      String(catalog.bsr),
      catalog.bsr_category,
    ]);
    if (!bsrResult.error) {
      estimatedMonthlySales = bsrResult.estimated_monthly_sales || 0;
      demandIndicator = bsrResult.demand_indicator || "N/A";
    }
  }

  // Size tier from dimensions
  const dims = catalog.dimensions || {};
  if (dims.length && dims.width && dims.height && dims.weight) {
    const maxSide = Math.max(dims.length, dims.width, dims.height);
    const weight = dims.weight;
    if (maxSide > 18 || weight > 20) {
      sizeTier = "Bulky";
    } else if (maxSide > 15 || weight > 12) {
      sizeTier = "Large Standard";
    } else {
      sizeTier = "Small Standard";
    }
  }

  // Profitability
  let profitPerUnit = null;
  let roi = null;
  let margin = null;
  let monthlyProfit = null;
  let totalCost = null;

  if (wholesaleCost != null && wholesaleCost > 0) {
    totalCost = wholesaleCost + PREP_COST + SHIPPING_PER_UNIT;
    profitPerUnit = buyBoxPrice - totalCost - totalFees;
    roi = (profitPerUnit / totalCost) * 100;
    margin = buyBoxPrice > 0 ? (profitPerUnit / buyBoxPrice) * 100 : 0;
    monthlyProfit = profitPerUnit * estimatedMonthlySales;
  }

  return {
    estimated_monthly_sales: estimatedMonthlySales,
    demand_indicator: demandIndicator,
    size_tier: sizeTier,
    total_cost: totalCost,
    profit_per_unit: profitPerUnit,
    roi,
    margin,
    monthly_profit: monthlyProfit,
    wholesale_cost: wholesaleCost,
  };
}

/**
 * Main product research workflow.
 * Triggered by: fba/research.requested
 */
const researchProduct = inngest.createFunction(
  {
    id: "fba/research-product",
    retries: 2,
  },
  { event: "fba/research.requested" },
  async ({ event, step }) => {
    const { query, asin, wholesale_cost: wc } = event.data || {};
    const wholesaleCost = wc != null ? parseFloat(wc) : null;

    // Step 1: Identify ASINs
    const asins = await step.run("identify-asins", () => {
      if (asin) {
        sendProgress(`[Research] Analizando ASIN: ${asin}...`);
        return [asin];
      }

      sendProgress(`[Research] Buscando productos: "${query}"...`);
      const searchResults = execTool("sp-api-query.py", [
        "catalog-search",
        ...query.split(" "),
      ]);

      if (searchResults.error) {
        sendProgress(
          `[Research] Error en búsqueda: ${searchResults.error.substring(0, 100)}`
        );
        return [];
      }

      // SP-API catalog-search returns items with ASINs directly
      const asinList = (Array.isArray(searchResults) ? searchResults : [])
        .map(item => item.asin)
        .filter(Boolean)
        .slice(0, 5);

      if (asinList.length === 0) {
        sendProgress(
          `[Research] No se encontraron productos para "${query}". Intenta con un ASIN específico.`
        );
      } else {
        sendProgress(
          `[Research] Encontrados ${asinList.length} productos. Analizando en detalle...`
        );
      }

      return asinList;
    });

    if (asins.length === 0) {
      sendProgress("[Research] No se encontraron productos para esta búsqueda. Intenta con términos más específicos (ej: 'kitchen gadgets under 20' o un ASIN como B07X6C9RMF).");
      return { products: 0, message: "No ASINs found" };
    }

    // Process each ASIN through deep analysis
    const results = [];

    for (const currentAsin of asins.slice(0, 5)) {
      // Step 2: Catalog data
      const catalog = await step.run(`catalog-${currentAsin}`, () => {
        sendProgress(`[Research] Buscando datos para ${currentAsin}...`);
        return execTool("sp-api-query.py", ["catalog-full", currentAsin]);
      });

      if (catalog.error) {
        sendProgress(
          `[Research] Error obteniendo datos de ${currentAsin}: ${catalog.error.substring(0, 80)}`
        );
        continue;
      }

      // Step 3: Competitive pricing
      const pricing = await step.run(`pricing-${currentAsin}`, () => {
        const shortTitle = (catalog.title || currentAsin).substring(0, 30);
        sendProgress(`[Research] 50% - Analizando precios para ${shortTitle}...`);
        return execTool("sp-api-query.py", [
          "competitive-summary",
          currentAsin,
        ]);
      });

      // Step 4: FBA fees
      const fees = await step.run(`fees-${currentAsin}`, () => {
        const price = pricing.buy_box_price || 0;
        sendProgress(`[Research] 75% - Calculando costos FBA...`);
        return execTool("sp-api-query.py", [
          "fees-estimate",
          currentAsin,
          String(price),
        ]);
      });

      // Step 5: BSR + profitability calculation
      const analysis = await step.run(`analysis-${currentAsin}`, () => {
        return calculateProfitability(catalog, pricing, fees, wholesaleCost);
      });

      // Step 6: Restrictions check (separate step for retry isolation)
      const restrictions = await step.run(
        `restrictions-${currentAsin}`,
        () => {
          return execTool("sp-api-query.py", ["restrictions", currentAsin]);
        }
      );

      results.push({
        ...catalog,
        ...pricing,
        ...fees,
        ...analysis,
        restrictions: restrictions.error ? { restricted: false, reasons: [] } : restrictions,
        asin: currentAsin,
      });
    }

    // Final: Send product cards sorted by ROI
    await step.run("send-results", () => {
      if (results.length === 0) {
        sendProgress(
          `[Research] No se pudieron analizar los productos. Verifica los ASINs e intenta de nuevo.`
        );
        return;
      }

      // Sort by ROI descending (null ROI goes last)
      results.sort((a, b) => {
        if (a.roi == null && b.roi == null) return 0;
        if (a.roi == null) return 1;
        if (b.roi == null) return -1;
        return b.roi - a.roi;
      });

      for (const product of results) {
        sendProductCard(product);
      }

      if (results.length > 1) {
        sendProgress(
          `[Research] Completado: ${results.length} productos analizados, ordenados por ROI.`
        );
      } else {
        sendProgress(`[Research] Análisis completado.`);
      }
    });

    await step.run("save-to-db", () => {
      execTool("research_db.py", [
        "save-research",
        JSON.stringify({
          source: "research",
          products: results,
        }),
      ]);
    });

    return {
      products: results.length,
      top_roi: results[0]?.roi,
      top_asin: results[0]?.asin,
    };
  }
);

module.exports = { functions: [researchProduct] };
