function toggle_actor_switch(actor_id){
    var paths = actor_id.split("_");
    var prop = 'auto'
    if(paths[4] == 'onoff') {
        prop = 'active'
    }
    onoff_switch_id = 'switch_' + paths.slice(1, -1).join('_') + '_onoff-switch'
    schedule_id = paths.slice(1, -1).join('_') + '_schedule'
    onoff_id = paths.slice(0, -1).join('_') + '_onoff'
    auto_id = paths.slice(0, -1).join('_') + '_auto'
    var auto_value = document.getElementById(auto_id).checked
    document.getElementById(onoff_id).disabled = auto_value
    if(auto_value) {
        document.getElementById(onoff_switch_id).style.width = '0px'
        document.getElementById(onoff_switch_id).style.height = '0px'
        document.getElementById(onoff_switch_id).style.border = '0px'
        document.getElementById(schedule_id).disabled = false;
        document.getElementById(schedule_id).style.color = 'black';
    } else {
        document.getElementById(onoff_switch_id).style.width = ''
        document.getElementById(onoff_switch_id).style.height = ''
        document.getElementById(onoff_switch_id).style.border = ''
        document.getElementById(schedule_id).disabled = true;
        document.getElementById(schedule_id).style.color = 'grey';
    }
    $.post(
        paths.slice(1, -2).join('/') + '/actor/' + paths[3] + '/' + prop,
        {value: document.getElementById(actor_id).checked}
    );
}


function set_actor_limit(agent, zone, actor, limit_type, limit_value){
    $.post(
        [agent, zone, 'actor', actor, limit_type].join('/'),
        {value: $.toJSON(parseInt(limit_value))}
    );
}


function set_actor_schedule(actor_id){
    var paths = actor_id.split("_");
    $.post(
        paths.slice(0, 2).join('/') + '/actor/' + paths[2] + '/schedule',
        {value: $.toJSON(document.getElementById(actor_id).value)}
    );
}
