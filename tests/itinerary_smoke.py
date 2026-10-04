"""Browser regression checks; run with the app served on port 3000.
Requires Python Playwright >=1.45 and Chromium. Uses isolated browser storage
and stubs family-note requests, so no real Notion records are changed.
"""
import json
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect

BASE=os.environ.get('TIDE_LOG_TEST_URL','http://127.0.0.1:3000/itinerary')
CHROMIUM=os.environ.get('TIDE_LOG_CHROMIUM') or shutil.which('chromium')
KEY='tidelog_itinerary_v1'
def boot(context):
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/api/comments',lambda r:r.fulfill(json={'comments':[{'day':'Day 1','text':'Existing family note'}]}))
    page.goto(BASE,wait_until='domcontentloaded')
    expect(page.locator('.day-section:visible')).to_have_count(1)
    return page,errors
def order(page):
    return page.locator('#s-day1 .stop-card').evaluate_all('(cards)=>cards.map(c=>c.dataset.id)')
def align(page):
    page.locator('#s-day1').evaluate('(e)=>e.scrollIntoView({block:"start"})')
def select(page,number):
    page.locator('.day-shortcuts button[data-day="'+str(number)+'"]').click()
    expect(page.locator('#s-day'+str(number))).to_be_visible()

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=CHROMIUM,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':390,'height':844},accept_downloads=True)
    context.add_init_script('if (window === window.top) localStorage.setItem("tidelog_expenses_v1", localStorage.getItem("tidelog_expenses_v1") || "[{\\"name\\":\\"Existing expense\\"}]")')
    page,errors=boot(context)
    expect(page.locator('#s-day1')).to_be_visible()
    assert page.locator('#s-cover .info-panel').get_attribute('open') is None
    assert page.locator('.support-panel[open]').count()==0
    assert page.locator('#daysContainer iframe[src]').count()==0
    expect(page.locator('.day-shortcuts button')).to_have_count(6)
    for width in [320,390,768,1440]:
        page.set_viewport_size({'width':width,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth')==width
    page.set_viewport_size({'width':390,'height':844})
    select(page,4)
    expect(page.locator('#s-day4')).to_contain_text('QSNGSK')
    assert page.locator('#s-day4 .stop-card').count()==11
    select(page,1)
    page.locator('#s-day1 .edit-stop').first.click()
    payload='Lunch <img src=x onerror="window.testXss=true"> & sushi'
    page.locator('#field-t').fill('13:10')
    page.locator('#field-a').fill(payload)
    page.locator('#field-n').fill('Remember reservation\nQSNGSK')
    page.locator('#field-loc').fill('Naha test address')
    page.locator('#editForm .save').click()
    expect(page.locator('#editDialog')).not_to_be_visible()
    expect(page.locator('#s-day1 .stop-time').first).to_have_text('13:10')
    expect(page.locator('#s-day1 .stop-title').first).to_contain_text(payload)
    assert page.locator('#s-day1 .stop-card img').count()==0
    assert page.evaluate('window.testXss') is None
    route=parse_qs(urlparse(page.locator('#s-day1 .btn-directions').get_attribute('href')).query)
    assert route['origin']==['Naha test address']
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('#s-day1 .stop-time').first).to_have_text('13:10')
    expect(page.locator('#s-day1 .stop-title').first).to_contain_text(payload)
    page.locator('#s-day1 .stop-details summary').first.click()
    expect(page.locator('#s-day1 .stop-note').first).to_contain_text('Remember reservation\nQSNGSK')
    page.locator('#s-day1 .stop-details summary').first.click()
    print('PASS compact single-day layout, six shortcuts, edit all four fields, reload persistence and safe text rendering')

    # Mouse drag, then real keyboard movement, preserving item text/time.
    align(page)
    before=order(page)
    handle=page.locator('#s-day1 .drag-handle').first.bounding_box()
    target=page.locator('#s-day1 .stop-card').nth(2).bounding_box()
    page.mouse.move(handle['x']+handle['width']/2,handle['y']+handle['height']/2)
    page.mouse.down()
    page.mouse.move(handle['x']+handle['width']/2,target['y']+target['height']-5,steps=18)
    page.mouse.up()
    assert order(page)==before[1:3]+[before[0]]+before[3:], order(page)
    moved=page.locator('#s-day1 [data-id="'+before[0]+'"]')
    expect(moved.locator('.stop-time')).to_have_text('13:10')
    page.reload(wait_until='domcontentloaded')
    assert order(page)[2]==before[0]
    moved=page.locator('#s-day1 [data-id="'+before[0]+'"]')
    moved.locator('.drag-handle').focus()
    page.keyboard.press('ArrowUp')
    assert order(page)[1]==before[0]
    page.locator('#undoBtn').click()
    assert order(page)[2]==before[0]
    page.locator('#s-day1 .move-buttons button[data-action="down"]').first.click()
    assert order(page)[1]==before[1]
    print('PASS mouse drag, keyboard arrows, move buttons, undo, order persistence and unchanged times')

    # Backup round trip; cancellation does not change data, invalid imports retain edits.
    with page.expect_download() as download:
        page.locator('#exportBtn').click()
    backup=json.loads(Path(download.value.path()).read_text())
    assert backup['days']['1']['overrides'][before[0]]['a']==payload
    page.on('dialog',lambda dialog:dialog.accept())
    page.locator('#s-day1 [data-action="reset"]').click()
    assert order(page)==before
    expect(page.locator('#s-day1 .stop-title').first).not_to_contain_text(payload)
    page.locator('#importFile').set_input_files({'name':'backup.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
    expect(page.locator('#saveStatus')).to_contain_text('備份已匯入')
    expect(page.locator('#s-day1 [data-id="'+before[0]+'"] .stop-title')).to_contain_text(payload)
    stored=page.evaluate('(key)=>localStorage.getItem(key)',KEY)
    page.locator('#importFile').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'{"version":1,"days":{"1":{"order":["not-a-real-id"]}}}'})
    expect(page.locator('#saveStatus')).to_contain_text('無法匯入')
    assert page.evaluate('(key)=>localStorage.getItem(key)',KEY)==stored
    page.locator('#s-day1 .edit-stop').first.click()
    page.locator('#field-t').fill('UNSAVED')
    page.locator('#cancelEdit').click()
    assert page.evaluate('(key)=>localStorage.getItem(key)',KEY)==stored
    assert page.evaluate('JSON.parse(localStorage.getItem("tidelog_expenses_v1"))[0].name')=='Existing expense'
    expect(page.locator('#s-day1 .dc-text')).to_have_value('Existing family note')
    print('PASS export/import backup, per-day reset, invalid import/cancel safety, existing expenses and family notes preserved')

    # Today uses Japan timezone; selected day survives reload; printing includes all days.
    page.clock.set_fixed_time(datetime(2026,10,10,15,30,tzinfo=timezone.utc))
    page.locator('#todayBtn').click()
    expect(page.locator('#s-day5')).to_be_visible() # Japan: 10/11 00:30; Hong Kong still 10/10
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('#s-day5')).to_be_visible()
    page.evaluate('window.dispatchEvent(new Event("beforeprint"))')
    page.emulate_media(media='print')
    assert page.locator('.day-section:visible').count()==6
    assert page.locator('.stop-details:not([open])').count()==0
    page.emulate_media(media='screen')
    page.evaluate('window.dispatchEvent(new Event("afterprint"))')
    assert page.locator('.day-section:visible').count()==1
    page.evaluate('navigator.serviceWorker.ready')
    page.wait_for_function('navigator.serviceWorker.controller !== null')
    context.set_offline(True)
    page.reload(wait_until='domcontentloaded')
    select(page,1)
    expect(page.locator('#s-day1 [data-id="'+before[0]+'"] .stop-title')).to_contain_text(payload)
    assert not errors,errors
    print('PASS Japan-date today shortcut, selected-day persistence, all-day printing, and editing available offline')
    context.close()

    # Native touch gestures, with scroll/pointer capture rather than HTML5-only desktop drag.
    mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    page,errors=boot(mobile)
    select(page,1)
    align(page)
    before=order(page)
    session=mobile.new_cdp_session(page)
    handle=page.locator('#s-day1 .drag-handle').first.bounding_box()
    target=page.locator('#s-day1 .stop-card').nth(2).bounding_box()
    x=handle['x']+handle['width']/2
    y=handle['y']+handle['height']/2
    end=target['y']+target['height']-5
    session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
    for i in range(1,13):
        session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y+(end-y)*i/12}]})
    session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    assert order(page)==before[1:3]+[before[0]]+before[3:],order(page)
    page.reload(wait_until='domcontentloaded')
    assert order(page)[2]==before[0]
    align(page)
    current=order(page)
    handle=page.locator('#s-day1 .drag-handle').first.bounding_box()
    target=page.locator('#s-day1 .stop-card').nth(1).bounding_box()
    x=handle['x']+handle['width']/2;y=handle['y']+handle['height']/2
    session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
    session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':target['y']+target['height']-5}]})
    session.send('Input.dispatchTouchEvent',{'type':'touchCancel','touchPoints':[]})
    assert order(page)==current
    assert not errors,errors
    print('PASS real touch drag on mobile, persistence and cancelled-gesture rollback')
    mobile.close()

    # Unavailable storage is reported; corrupted existing data is not silently deleted at startup.
    failing=browser.new_context(viewport={'width':390,'height':844})
    failing.add_init_script('const original=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==="tidelog_itinerary_v1")throw new Error("Quota exceeded");return original.call(this,k,v)}')
    page,errors=boot(failing)
    page.locator('#s-day1 .edit-stop').first.click()
    page.locator('#field-a').fill('Unsaved but exportable')
    page.locator('#editForm .save').click()
    expect(page.locator('#saveStatus')).to_contain_text('未能儲存')
    with page.expect_download() as download:
        page.locator('#exportBtn').click()
    assert json.loads(Path(download.value.path()).read_text())['days']['1']['overrides']['d1-stop-1']['a']=='Unsaved but exportable'
    assert not errors,errors
    failing.close()
    corrupt=browser.new_context()
    corrupt.add_init_script('if (window === window.top) localStorage.setItem("tidelog_itinerary_v1","CORRUPTED")')
    page,errors=boot(corrupt)
    assert page.evaluate('localStorage.getItem("tidelog_itinerary_v1")')=='CORRUPTED'
    expect(page.locator('#saveStatus')).to_contain_text('未能讀取')
    assert not errors,errors
    corrupt.close()
    print('PASS storage-failure reporting/export fallback and corrupt-data protection')
    browser.close()
