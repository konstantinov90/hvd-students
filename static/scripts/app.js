var form = {
    selectedInp: document.getElementById('selected'),
    dayIdInp: document.getElementById('day-id'),
    periodInp: document.getElementById('period'),
    groupInp: document.getElementById('group'),
    studentIdInp: document.getElementById('student-id'),
    labIdInp: document.getElementById('lab-id'),
};
var modal = document.getElementById('myModal');

function removeClassGlobally(className) {
    document.querySelectorAll('.' + className).forEach(function (el) {
        el.classList.remove(className);
    });
}

function inactivate() {
    removeClassGlobally('active');
    selectedInp.value = '';
}

function sign(el, periodNum, url) {
    modal.style.display = 'block';

    var tr = el.parentElement;
    var period = tr.parentElement.parentElement.parentElement;
    var day = period.parentElement.parentElement;
    var dayStr = day.querySelector('.day-header').querySelector('h2').innerHTML;
    var periodStr = period.querySelector('h4').innerHTML;

    form.selectedInp.value = dayStr + ' ' + periodStr;
    form.dayIdInp.value = day.id;
    form.periodInp.value = periodNum;
    form.labIdInp.value = tr.querySelector('td').innerHTML;

    tr.classList.add('active');

    var formData = new FormData();

    formData.append(form.selectedInp.id, form.selectedInp.value);
    formData.append(form.dayIdInp.id, form.dayIdInp.value);
    formData.append(form.periodInp.id, form.periodInp.value);
    formData.append(form.groupInp.id, form.groupInp.value);
    formData.append(form.studentIdInp.id, form.studentIdInp.value);
    formData.append(form.labIdInp.id, form.labIdInp.value);

    // for (f in form) {
    //     formData.append(form[f].id, form[f].value);
    // }
    fetch(url, {
        method: 'POST',
        body: formData,
        credentials: "same-origin",
    }).then(function (d) {
        if (d.status == 200) {
            window.location = '/';
            return d.text();
        } else {
            return d.text();
        }
    }).then(function(d) {
        var content = modal.querySelector('.modal-content');
        content.innerHTML = d + ' <p>вскоре вы будете перемещены...</p>';
        setTimeout(function() {
            window.location = '/';
        }, 5000);
    })
    .catch(function(e) {
        console.error(e);
    });
}

function signUp(el, periodNum) {
    sign(el, periodNum, '/rest/register/');
}

function signOut(el, periodNum) {
    var criticalTime = new Date(el.parentElement.attributes['critical-time'].value);
    var blockUntilTime = el.parentElement.attributes['block-until'].value;
    var now = new Date();
    var msg = "Вы уверены?" + (now > criticalTime? "\nCледующая возможность записаться на отработку данной ЛР будет предоставлена Вам " + blockUntilTime + "!": "");
    if (confirm(msg)) {
        sign(el, periodNum, '/rest/unregister/');
    }
}

function logOff() {
    var cookies = document.cookie.split(";");

    for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i];
        if (cookie.split('=')[0] === 'AUTH_TKT') {
            var newCookie = 'AUTH_TKT=;expires=Thu, 01 Jan 1970 00:00:00 GMT';
            document.cookie = document.cookie.replace(cookie, newCookie);
        }
        window.location = '/';
    }
}

function timeout(ms, promise) {
    return new Promise(function(resolve, reject) {
      setTimeout(function() {
        reject(new Error("timeout"));
      }, ms);
      promise.then(resolve, reject);
    });
  }

var hash;
fetch('/heartbeat/?hash=').then(function (d) {return d.text()}).then(function (t) {
    hash = t;
    heartbeat();
}).catch(function (e) {
    window.location = '/';
});


function heartbeat() {
    var timeStampInMs = window.performance && window.performance.now && window.performance.timing && window.performance.timing.navigationStart ? window.performance.now() + window.performance.timing.navigationStart : Date.now();
    Promise.race([
        fetch('/heartbeat/?hash=' + hash + "&_ts=" + timeStampInMs),
        new Promise(function(resolve, reject) {
            setTimeout(function() {return reject(new Error('request timeout'))}, 10000);
        }),
    ]).then(function (d) {
        return d.text();
    }).then(function (t) {
        window.location = '/';
    }).catch(function (e) {
        setTimeout(heartbeat, 1000);
    });
}