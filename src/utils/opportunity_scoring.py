"""
Opportunity Scoring Engine
Ranks trades by ROI, inclusion chance, competition risk, liquidity
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class ScoredOpportunity:
    """Opportunity with score"""
    opportunity: Dict
    total_score: float
    roi_score: float
    inclusion_score: float
    competition_score: float
    liquidity_score: float
    risk_score: float
    reasons: List[str]


class OpportunityScorer:
    """
    Advanced opportunity scoring engine
    Ranks trades by multiple factors for optimal execution
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Scoring weights (can be tuned)
        self.weights = {
            "roi": 0.35,
            "inclusion": 0.25,
            "competition": 0.20,
            "liquidity": 0.10,
            "risk": 0.10
        }
        
        # Historical data for scoring
        self.opportunity_history = []
    
    async def score_opportunities(
        self,
        opportunities: List[Dict]
    ) -> List[ScoredOpportunity]:
        """
        Score and rank all opportunities
        Returns sorted by total score
        """
        scored = []
        
        for opp in opportunities:
            score = await self._score_single_opportunity(opp)
            scored.append(score)
        
        # Sort by total score
        scored.sort(key=lambda x: x.total_score, reverse=True)
        
        return scored
    
    async def _score_single_opportunity(
        self,
        opportunity: Dict
    ) -> ScoredOpportunity:
        """Score a single opportunity"""
        
        opp_type = opportunity.get("type", "unknown")
        
        # Calculate individual scores
        roi_score = self._calculate_roi_score(opportunity)
        inclusion_score = self._calculate_inclusion_score(opportunity)
        competition_score = self._calculate_competition_score(opportunity)
        liquidity_score = self._calculate_liquidity_score(opportunity)
        risk_score = self._calculate_risk_score(opportunity)
        
        # Calculate weighted total
        total_score = (
            roi_score * self.weights["roi"] +
            inclusion_score * self.weights["inclusion"] +
            competition_score * self.weights["competition"] +
            liquidity_score * self.weights["liquidity"] +
            risk_score * self.weights["risk"]
        )
        
        # Generate reasons
        reasons = self._generate_reasons(opportunity, {
            "roi": roi_score,
            "inclusion": inclusion_score,
            "competition": competition_score,
            "liquidity": liquidity_score,
            "risk": risk_score
        })
        
        return ScoredOpportunity(
            opportunity=opportunity,
            total_score=total_score,
            roi_score=roi_score,
            inclusion_score=inclusion_score,
            competition_score=competition_score,
            liquidity_score=liquidity_score,
            risk_score=risk_score,
            reasons=reasons
        )
    
    def _calculate_roi_score(self, opportunity: Dict) -> float:
        """Calculate ROI score (0-1)"""
        
        profit = opportunity.get("expected_profit", 0)
        amount = opportunity.get("amount_in", 1)
        
        if amount == 0:
            return 0
        
        roi = profit / amount
        
        # Normalize: 10%+ = 1.0, 0% = 0
        roi_score = min(roi / 0.10, 1.0)
        
        return roi_score
    
    def _calculate_inclusion_score(self, opportunity: Dict) -> float:
        """Calculate chance of block inclusion (0-1)"""
        
        # Factors that affect inclusion:
        # - Gas price offered
        # - Gas strategy (urgent vs slow)
        # - Time to block
        # - Bundle complexity
        
        gas_price = opportunity.get("gas_price", 0)
        urgency = opportunity.get("urgency", "normal")
        
        # Base score from gas
        if gas_price > 100:  # High gas
            gas_score = 1.0
        elif gas_price > 50:
            gas_score = 0.7
        elif gas_price > 20:
            gas_score = 0.4
        else:
            gas_score = 0.2
        
        # Urgency multiplier
        urgency_mult = {
            "urgent": 1.0,
            "fast": 0.9,
            "normal": 0.7,
            "slow": 0.3
        }.get(urgency, 0.5)
        
        # Bundle complexity
        bundle_size = opportunity.get("bundle_size", 1)
        complexity_score = 1.0 / bundle_size  # Smaller bundles = faster
        
        return min(gas_score * urgency_mult * complexity_score, 1.0)
    
    def _calculate_competition_score(self, opportunity: Dict) -> float:
        """Calculate competition risk (0-1, higher = more competition)"""
        
        # Factors:
        # - Opportunity type (liquidation = more competition)
        # - Protocol (popular = more bots)
        # - Time of day
        
        opp_type = opportunity.get("type", "")
        
        # Base competition by type
        type_competition = {
            "liquidation": 0.8,  # High competition
            "arbitrage": 0.5,     # Medium
            "sandwich": 0.3,      # Lower
            "cross_chain": 0.2    # Lower
        }.get(opp_type, 0.5)
        
        # Protocol popularity
        protocol = opportunity.get("protocol", "").lower()
        
        popular_protocols = ["aave", "compound", "uniswap"]
        if any(p in protocol for p in popular_protocols):
            type_competition += 0.1
        
        # Time factor (US trading hours = more competition)
        current_hour = time.localtime().tm_hour
        if 14 <= current_hour <= 21:  # 2PM-9PM UTC = US hours
            type_competition += 0.1
        
        return min(type_competition, 1.0)
    
    def _calculate_liquidity_score(self, opportunity: Dict) -> float:
        """Calculate liquidity score (0-1)"""
        
        # Higher liquidity = lower slippage = better
        liquidity = opportunity.get("liquidity", 0)
        
        # Normalize: $1M+ = 1.0, $0 = 0
        if liquidity > 1_000_000:
            return 1.0
        elif liquidity > 100_000:
            return 0.7
        elif liquidity > 10_000:
            return 0.4
        elif liquidity > 1000:
            return 0.2
        else:
            return 0.1
    
    def _calculate_risk_score(self, opportunity: Dict) -> float:
        """Calculate risk score (0-1)"""
        
        # Lower risk = higher score
        risk_factors = 0
        
        # Contract risk
        if opportunity.get("verified_contract", True) == False:
            risk_factors += 0.3
        
        # Slippage risk
        if opportunity.get("expected_slippage", 0) > 0.05:
            risk_factors += 0.2
        
        # Gas risk
        if opportunity.get("gas_volatility", 0) > 0.5:
            risk_factors += 0.2
        
        # Revert risk
        if opportunity.get("revert_probability", 0) > 0.1:
            risk_factors += 0.3
        
        return 1.0 - min(risk_factors, 1.0)
    
    def _generate_reasons(
        self,
        opportunity: Dict,
        scores: Dict
    ) -> List[str]:
        """Generate human-readable reasons for scores"""
        
        reasons = []
        
        # ROI reasons
        if scores["roi"] > 0.8:
            reasons.append("Excellent ROI")
        elif scores["roi"] < 0.3:
            reasons.append("Low ROI")
        
        # Competition reasons
        if scores["competition"] > 0.7:
            reasons.append("High competition risk")
        elif scores["competition"] < 0.3:
            reasons.append("Low competition")
        
        # Liquidity reasons
        if scores["liquidity"] < 0.3:
            reasons.append("Low liquidity - high slippage risk")
        
        # Risk reasons
        if scores["risk"] < 0.5:
            reasons.append("High risk detected")
        
        return reasons
    
    def get_best_opportunity(
        self,
        opportunities: List[Dict]
    ) -> Optional[ScoredOpportunity]:
        """Get the best opportunity by score"""
        
        if not opportunities:
            return None
        
        scored = asyncio.run(self.score_opportunities(opportunities))
        
        return scored[0] if scored else None
    
    def update_weights(self, new_weights: Dict):
        """Update scoring weights"""
        for key, value in new_weights.items():
            if key in self.weights:
                self.weights[key] = value
    
    def get_weights(self) -> Dict:
        """Get current weights"""
        return self.weights.copy()


class AdaptiveScorer:
    """
    Adaptive scorer that learns from results
    """
    
    def __init__(self, base_scorer: OpportunityScorer):
        self.base_scorer = base_scorer
        self.performance_history = []
    
    def record_result(
        self,
        scored_opp: ScoredOpportunity,
        actual_profit: float,
        success: bool
    ):
        """Record actual result for learning"""
        
        self.performance_history.append({
            "timestamp": time.time(),
            "predicted_score": scored_opp.total_score,
            "actual_profit": actual_profit,
            "success": success,
            "opportunity_type": scored_opp.opportunity.get("type")
        })
    
    def get_optimal_strategy(self) -> Dict:
        """Learn optimal strategy from history"""
        
        if len(self.performance_history) < 10:
            return self.base_scorer.get_weights()
        
        # Analyze by opportunity type
        type_performance = {}
        
        for result in self.performance_history:
            opp_type = result["opportunity_type"]
            
            if opp_type not in type_performance:
                type_performance[opp_type] = []
            
            type_performance[opp_type].append(result)
        
        # Adjust weights based on performance
        optimized_weights = self.base_scorer.get_weights()
        
        for opp_type, results in type_performance.items():
            success_rate = sum(1 for r in results if r["success"]) / len(results)
            avg_profit = sum(r["actual_profit"] for r in results) / len(results)
            
            # Boost weights for successful types
            if success_rate > 0.7 and avg_profit > 100:
                optimized_weights["roi"] += 0.05
            elif success_rate < 0.3:
                optimized_weights["roi"] -= 0.05
        
        # Normalize weights
        total = sum(optimized_weights.values())
        optimized_weights = {k: v/total for k, v in optimized_weights.items()}
        
        return optimized_weights


# Factory
def create_opportunity_scorer(config: Dict) -> OpportunityScorer:
    """Create opportunity scorer"""
    return OpportunityScorer(config)
