# License for this script is the CC BY-NC-SA 2.5: https://creativecommons.org/licenses/by-nc-sa/2.5/
# The original author of this script is Danny, of PvXwiki: http://gwpvx.gamepedia.com/UserProfile:Danny11384
import httplib
import re
import os
import os.path
import urllib

conn = httplib.HTTPConnection('gwpvx.gamepedia.com')
parameters = raw_input('Parameters: ')

def main():
    global conn
    global parameters
    conn.request('GET', '/PvX_wiki')
    r1 = conn.getresponse()
    conn.close()
    if r1.status == 200:
        print_log("Holy shit! Curse is actually working. Now let's start getting that build data.", 'yes')
    else:
        httpfaildebugger('Start', r1.status, r1.response, r1.getheaders())

    #Check for category selection mode. 'q' takes priority over 'c'. If neither, just grab the tested builds.
    if parameters.find('q') > -1:
        CATEGORIES = [(raw_input('Enter category: ')).replace(' ','_')]
    elif parameters.find('c') > -1:
        CATEGORIES = category_selection(['All_working_PvP_builds', 'All_working_PvE_builds', 'Archived_tested_builds', 'Trash_builds', 'Untested_testing_builds', 'Trial_Builds', 'Build_stubs', 'Abandoned', 'Costume_Brawl_builds'])
        if not 'All_working_PvP_builds' in CATEGORIES:
            CATEGORIES += category_selection(['All_working_AB_builds', 'All_working_FA_builds', 'All_working_JQ_builds', 'All_working_RA_builds', 'All_working_GvG_builds', 'All_working_HA_builds', 'All_working_PvP_team_builds'])
        if not 'All_working_PvE_builds' in CATEGORIES:
            CATEGORIES += category_selection(['All_working_general_builds', 'All_working_hero_builds', 'All_working_SC_builds', 'All_working_running_builds', 'All_working_farming_builds', 'All_working_PvE_team_builds', ])
        # If no categories were selected, give the opportunity for a custom category input.
        if len(CATEGORIES) < 1:
            answer = raw_input('Well what DO you want to compile? ')
            if answer == '':
                print_log('No category entered.', 'yes')
            else:
                print_log('I hope you typed that correctly.', 'yes')
                CATEGORIES += [answer.replace(' ','_')]
    else:
        CATEGORIES = ['All_working_PvP_builds', 'All_working_PvE_builds']

    if not os.path.isdir('./PvX Build Packs'):
        os.mkdir('./PvX Build Packs')

    pagelist = []
    for cat in CATEGORIES:
        # This done so you don't have a massive page id displayed for category continuations.
        catname = re.sub(r'&cmcontinue=page\|.*\|.*', '', cat)
        print_log("Assembling build list for " + catname.replace('_',' ') + "...")
        conn.request('GET', '/api.php?action=query&format=json&list=categorymembers&cmlimit=max&cmtitle=Category:' + cat)
        response = conn.getresponse()
        page = response.read()
        conn.close()
        # Check if a continuation was offered due to the category having more members than the display limit
        continuestr = re.search(r'(page\|.*\|.*)",', page)
        if continuestr:
            CATEGORIES += [catname + '&cmcontinue=' + continuestr.group(1)]
        if response.status == 200:
            pagelist = category_page_list(page, pagelist)
            print_log("Builds from " + catname.replace('_',' ') + " added to list!")
        else:
            httpfaildebugger(cat, response.status, response.reason, response.getheaders())
            print_log("Build listing for " + catname.replace('_',' ') + " failed.")
    print_log(str(len(pagelist)) + ' builds found!', 'yes')

    # Check for limit directory mode
    if parameters.find('l') > -1:
        gametypes = [raw_input('Limit output to directory: ')]
        while gametypes[0] == '' or (len(re.findall('[/\\\\*?:"<>|.]', gametypes[0])) > 0):
            gametypes = [raw_input('Invalid directory name. Please choose another name: ')]

    # Process the builds
    for i in pagelist:
        # Check to see if the build has an empty primary profession (would generate an invalid template code)
        if i.find('Any/') > -1:
            print_log(i + " skipped (empty primary profession).")
        else:
            print_log("Attempting " + (urllib.unquote(i)).replace('_',' ') + "...")
            conn.request('GET', '/' + i.replace(' ','_').replace('\'','%27').replace('"','%22'))
            response = conn.getresponse()
            page = response.read()
            conn.close()
            if response.status == 200:
                # Grab the build info, but prevent overwriting 'l' if it was set
                if parameters.find('l') == -1:
                    gametypes = id_gametypes(page)
                ratings = id_ratings(page)
                codes = re.findall('<input id="gws_template_input" type="text" value="(.*?)"', page)
                # If no template codes found on the build page, skip the build
                if len(codes) == 0:
                    print_log('No template code found for ' + i + '. Skipped.')
                    continue
                # Establish directories
                directories = []
                for typ in gametypes:
                    if len(typ) > 3 and typ.find('team') == -1:
                        typdir = './PvX Build Packs/' + typ.title()
                    else:
                        typdir = './PvX Build Packs/' + typ
                    if not os.path.isdir(typdir):
                        os.mkdir(typdir)
                    # Check for no ratings mode
                    if parameters.find('r') == -1:
                        for rat in ratings:
                            directories += [typdir + '/' + rat]
                        rateinname = ''
                    else:
                        directories += [typdir]
                        rateinname = ' - ' + str(ratings).replace('[','').replace(']','').replace("'",'').replace(',','-').replace(' ','')
                # Check for debug mode
                if parameters.find('d') > -1:
                    gbawdebugger(i, gametypes, ratings, codes, directories)
                for d in directories:
                    if not os.path.isdir(d):
                        os.mkdir(d)
                # Check to see if the build is a team build
                if i.find('Team') >= 1 and len(codes) > 1:
                    num = 0
                    for j in codes:
                        num += 1
                        for d in directories:
                            #Adds the team folder
                            teamdir = file_name_sub(i, d) + rateinname
                            if not os.path.isdir(teamdir):
                                os.mkdir(teamdir)
                            outfile = open(file_name_sub(i, teamdir) + ' - ' + str(num) + '.txt','wb')
                            outfile.write(j)
                else:
                    for d in directories:
                        # Check for a non-team build with both player and hero versions, and sort them appropriately
                        if len(codes) > 1 and ('hero' in gametypes) and ('general' in gametypes) and d.find('Hero') > -1:
                            outfile = open(file_name_sub(i, d) + ' - Hero' + rateinname + '.txt','wb')
                            outfile.write(codes[1])
                        else:
                            outfile = open(file_name_sub(i, d) + rateinname + '.txt','wb')
                            outfile.write(codes[0])
                print_log(i + " complete.")
            elif response.status == 301:
                # Inserts the redirected build name into the pagelist array so it is done next
                headers = str(response.getheaders())
                newpagestr = re.findall("gwpvx.gamepedia.com/.*?'\)", headers)
                newpagename = newpagestr[0].replace('gwpvx.gamepedia.com/','').replace("')",'').replace('_',' ')
                newpagepos = pagelist.index(i) + 1
                pagelist.insert(newpagepos, newpagename)
                print_log('301 redirection...')
            else:
                httpfaildebugger(i, response.status, response.reason, response.getheaders())
                print_log(i + " failed.")
    print_log("Script complete.", 'yes')

def file_name_sub(build, directory):
    #Handles required substitutions for build filenames
    filename = directory + '/' + (urllib.unquote(build)).replace('Build:','').replace('Archive:','').replace('/','_').replace('"','\'\'')
    return filename

def category_selection(ALLCATS):
    CATEGORIES = []
    for a in ALLCATS:
        answer = raw_input('Would you like to compile ' + a.replace('_',' ') + '? (y/n) ')
        if answer == 'y':
            CATEGORIES += [a]
    return CATEGORIES

def category_page_list(page, newlist):
    pagelist = re.findall('"(Build:.*?)"\}', page) + re.findall('"(Archive:.*?)"\}', page)
    for i in pagelist:
        current = i.replace('\\','')
        if not current in newlist:
            newlist += [current]
    return newlist

def id_gametypes(page):
    # Finds the build-types div, and then extracts the tags. Two checks for: build-types div isn't found or if it has no tags in it.
    builddiv = re.search('<div class="build-types">.*?</div>', page, re.DOTALL)
    if not builddiv:
        return ['Uncategorized']
    rawtypes = re.findall('Pv[EP]<br />\w+', builddiv.group())
    if len(rawtypes) == 0:
        return ['Uncategorized']
    # Build the gametypes list based on the tags
    gametypes = []
    for t in rawtypes:
        if t.find('team') > -1:
            gametypes += [re.sub('<br />', ' ', t)]
        else:
            gametypes += [re.sub('Pv[EP]<br />', '', t)]
    return gametypes

def id_ratings(page): 
    ratings = []
    if page.find('This build is part of the current metagame.') > -1:
        ratings += ['Meta']
    #A second if statement because builds can have both Meta and one of Good/Great
    if page.find('in the range from 4.75') > -1:
        ratings += ['Great']
    elif page.find('in the range from 3.75') > -1:
        ratings += ['Good']
    elif page.find('below 3.75') > -1:
        ratings += ['Trash']
    elif page.find('in the <i>trial</i> phase.') > -1:
        ratings += ['Trial']
    elif page.find('This build is currently being tested.') > -1:
        ratings += ['Testing']
    elif page.find('been archived') > -1:
        ratings += ['Archived']
    if ratings == []:
        ratings = ['Nonrated']
    return ratings

def print_log(string, alwaysdisplay = 'no'):
    if (parameters.find('z') == -1) or (alwaysdisplay == 'yes'):
        print string
    if parameters.find('w') > -1:
        textlog = open('./buildpackslog.txt', 'ab')
        textlog.write(string + '\r\n')

def httpfaildebugger(attempt, response, reason, headers):
    debuglog = open('./buildpackshttpdebug.txt', 'ab')
    debuglog.write(str(attempt) + '\r\n' + str(response) + ' - ' + str(reason) + '\r\n' + str(headers) + '\r\n' + '----' + '\r\n')
    print_log('HTTPConnection error encountered: ' + str(response) + ' - ' + str(reason), 'yes')
    if attempt == 'Start':
        print_log("Curse's servers are (probably) down. Try again later.", 'yes')
        raise SystemExit()
    # Require a definitive answer from the user
    answer = ''
    while not answer == ('y' or 'n'):
        answer = raw_input('Do you wish to continue the script? ' + str(attempt) + ' will be skipped. (y/n) ')
        if answer == 'y':
            print_log('Ok, continuing...', 'yes')
        elif answer == 'n':
            print_log('Ok, exiting...', 'yes')
            raise SystemExit()
        else:
            print_log('Please enter \'y\' or \'n\'.', 'yes')

def gbawdebugger(build, gametypes, ratings, codes, directories):
    if parameters.find('s') == -1:
        # Write to a file
        debuglog = open('./buildpacksdebug.txt', 'ab')
        debuglog.write(build + '\r\n' + str(gametypes) + '\r\n' + str(ratings) + '\r\n' + str(codes) + '\r\n' + str(directories) + '\r\n----\r\n') 
    else:
        # Display in the window
        print_log(gametypes, 'yes')
        print_log(ratings, 'yes')
        print_log(codes, 'yes')
        print_log(directories, 'yes')

if __name__ == "__main__":
    main()
