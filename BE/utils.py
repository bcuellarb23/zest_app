#utils.py

def calculate_nutritional_data(goals, totals):
    """
    This standarizes nutritional math.
    Handles Decimal-to-FLoat conversion and prevents division by 0.
    """

    # This line converts my goals values to float so all my type values are consistent
    tdee = float(goals.get('tdee') or 0)
    proteins_goal = float(goals.get('max_proteins') or 0)
    carbs_goal = float(goals.get('max_carbs') or 0)
    fats_goal = float(goals.get('max_fats') or 0)
    
    # This convets my totals
    calories = float(totals.get('total_calories') or 0)
    proteins = float(totals.get('total_proteins') or 0)
    carbs = float(totals.get('total_carbs') or 0)
    fats = float(totals.get('total_fats') or 0)
    
    return {
        'tdee': tdee,
        'proteins_goal': proteins_goal,
        'carbs_goal': carbs_goal,
        'fats_goal': fats_goal,
        'consumed': {
            'calories': calories,
            'proteins': proteins,
            'carbs': carbs,
            'fats': fats,
            'calories_percentage': round((calories / tdee * 100), 2) if tdee > 0 else 0,
            'proteins_percentage': round((proteins / proteins_goal * 100), 2) if proteins_goal > 0 else 0,
            'carbs_percentage': round((carbs / carbs_goal * 100), 2) if carbs_goal > 0 else 0,
            'fats_percentage': round((fats / fats_goal * 100), 2) if fats_goal > 0 else 0,
        }
   }
