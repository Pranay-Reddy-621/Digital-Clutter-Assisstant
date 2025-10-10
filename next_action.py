# next_action.py
from file_sorter import FileSorter
 
class ActionDecider(FileSorter):
    def __init__(self):
        super().__init__()
        
    # Modified decide_action method
    def decide_action(self, filepath, window_info):
        variables = self.extract_variables(filepath, window_info)
        variables['category'] = self.determine_category(filepath, variables)

        for rule in sorted(self.rules, key=lambda x: x.get('priority', 1), reverse=True):
            if self.evaluate_rule(rule['condition'], variables):
                action = {
                    'type': rule['action']['type'],
                    'time': rule['action'].get('time')
                }

                # Add compress/extract to valid action types for target_path resolution
                if action['type'] in ['move', 'copy', 'compress', 'extract'] and 'target_path' in rule['action']:
                    action['target'] = self.resolve_template(
                        rule['action']['target_path'],
                        variables
                    )

                return action

        return {'type': 'no_action'}



def get_next_action(filepath, window_info):
    decider = ActionDecider()
    return decider.decide_action(filepath, window_info)

