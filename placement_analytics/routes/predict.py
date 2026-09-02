import math

from flask import render_template, request, session, flash

from ..decorators import login_required


def register(app):
    @app.route('/predict', methods=['GET', 'POST'])
    @login_required
    def predict():
        result = None
        if request.method == 'POST':
            try:
                cgpa       = float(request.form['cgpa'])
                skills     = request.form['skills']
                branch     = request.form.get('branch', 'CSE')
                backlogs   = int(request.form.get('backlogs', 0))
                internship = request.form.get('internship', 'no')
                projects   = int(request.form.get('projects', 0))

                if not math.isfinite(cgpa) or not 0.0 <= cgpa <= 10.0:
                    raise ValueError('CGPA must be between 0 and 10.')
                if backlogs < 0 or projects < 0:
                    raise ValueError('Backlogs and projects cannot be negative.')

                skill_list     = [s.strip().lower() for s in skills.split(',') if s.strip()]
                skill_count    = len(skill_list)
                high_demand    = ['python','java','react','node','sql','mysql','javascript',
                                  'dsa','c++','machine learning','ml','django','flask',
                                  'spring','aws','docker','git']
                matched_skills = sum(1 for s in skill_list if any(h in s for h in high_demand))

                if cgpa >= 9.5:   cgpa_score = 100
                elif cgpa >= 9.0: cgpa_score = 95
                elif cgpa >= 8.5: cgpa_score = 88
                elif cgpa >= 8.0: cgpa_score = 80
                elif cgpa >= 7.5: cgpa_score = 70
                elif cgpa >= 7.0: cgpa_score = 58
                elif cgpa >= 6.5: cgpa_score = 45
                elif cgpa >= 6.0: cgpa_score = 32
                else:             cgpa_score = 15

                skill_score  = min(100, (skill_count * 12) + (matched_skills * 8))
                branch_score = {'CSE':95,'IT':88,'ECE':75,'EEE':65,'Mechanical':55,'Civil':45}.get(branch, 60)

                if backlogs == 0:   backlog_score = 100
                elif backlogs == 1: backlog_score = 70
                elif backlogs == 2: backlog_score = 45
                elif backlogs <= 4: backlog_score = 20
                else:               backlog_score = 5

                internship_score = 100 if internship == 'yes' else 30
                project_score    = min(100, projects * 25)

                chance = round(
                    cgpa_score * 0.30 + skill_score * 0.25 + branch_score * 0.15 +
                    backlog_score * 0.15 + internship_score * 0.10 + project_score * 0.05
                )

                if chance >= 85:
                    company_matches = [
                        {'name':'Google / Amazon','icon':'🚀','color':'#10b981'},
                        {'name':'Microsoft / Adobe','icon':'⭐','color':'#2563eb'},
                        {'name':'TCS / Infosys','icon':'✅','color':'#10b981'},
                    ]
                elif chance >= 70:
                    company_matches = [
                        {'name':'Wipro / HCL','icon':'✅','color':'#10b981'},
                        {'name':'Capgemini / Accenture','icon':'⚡','color':'#f59e0b'},
                        {'name':'TCS / Infosys','icon':'✅','color':'#10b981'},
                    ]
                elif chance >= 50:
                    company_matches = [
                        {'name':'TCS / Infosys','icon':'✅','color':'#10b981'},
                        {'name':'Wipro / Tech Mahindra','icon':'⚡','color':'#f59e0b'},
                    ]
                else:
                    company_matches = [{'name':'Focus on improving skills first','icon':'📚','color':'#ef4444'}]

                tips = []
                if cgpa_score < 70:    tips.append('📈 Improve your CGPA — target 7.5+')
                if skill_count < 4:    tips.append('💻 Learn more in-demand skills (Python, DSA, SQL)')
                if matched_skills < 3: tips.append('🎯 Focus on: Python, Java, React, DSA')
                if backlogs > 0:       tips.append('📋 Clear all backlogs — they reduce chances significantly')
                if internship == 'no': tips.append('🏢 Try to get an internship — boosts chances by 10%')
                if projects < 2:       tips.append('🚀 Build at least 2-3 real projects')
                if not tips:           tips.append('🌟 You are well prepared — keep practicing DSA!')

                if chance >= 80:   level, color, emoji = 'High',     'green',  '🔥'
                elif chance >= 60: level, color, emoji = 'Medium',   'orange', '⚡'
                elif chance >= 40: level, color, emoji = 'Low',      'red',    '📚'
                else:              level, color, emoji = 'Very Low', 'red',    '😟'

                result = {
                    'chance':chance, 'level':level, 'color':color, 'emoji':emoji,
                    'cgpa':cgpa, 'skills':skill_count, 'matched_skills':matched_skills,
                    'branch':branch, 'backlogs':backlogs, 'internship':internship,
                    'projects':projects,
                    'scores':{'cgpa':round(cgpa_score),'skills':round(skill_score),
                              'branch':round(branch_score),'backlog':round(backlog_score),
                              'internship':round(internship_score),'projects':round(project_score)},
                    'company_matches':company_matches, 'tips':tips
                }
            except (KeyError, TypeError, ValueError) as e:
                flash(f'Error: {str(e)}', 'danger')
        return render_template('predict.html', result=result, user_name=session['user_name'])
