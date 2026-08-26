# Act IX drill 1 — three refusals, one of which is lying to you about its category
HINT='name the token claim the API server declined to accept — or, equally right, name the category
the 401 puts this failure in.'
CAUSE_SHA='adf0e0999386dae758e1d6ae48e7a28a1acfb26dd73dbc91ad134cec70ca7aa0
4275d71e90f7f09f9dcbba2aeeaafb3f30576780bc4d5419ff086d1c6f02a654
2b4c4ef08d33acb954eba4a09c6a7e87c74c1ab6bc5d50c180823821379f9b97
fd70c77d296e69492b56897f7ae1cc38c910b356e57e9b684bc8fd0f607f7fff
e2ad0af8a8f9fef14f784c1517353610be802a60cb0c0e43e0a186580642cd5f'

act9_env
require "the drill's probe ServiceAccount is still there" kubectl get sa probe

# The drill asks what would happen if somebody answered that 401 by granting more permissions. This
# runs it. `view` and not `cluster-admin`: the smallest grant that turns a 403 into a 200, so nothing
# alarming is left behind if this is interrupted.
GRANT=verify-act9-view
kubectl create clusterrolebinding "$GRANT" --clusterrole=view \
        --serviceaccount=default:probe >/dev/null 2>&1
PLAIN=$(api_status_settles 200 "$(kubectl create token probe --duration=1h 2>/dev/null)")
SCOPED=$(api_status "$(kubectl create token probe --audience=vault --duration=1h 2>/dev/null)")
kubectl delete clusterrolebinding "$GRANT" --ignore-not-found >/dev/null 2>&1

require_eq "granting read access does turn probe's ordinary token into a 200" 200 echo "$PLAIN"
require_eq "and the audience-scoped token is *still* 401 — a permission cannot repair this" 401 echo "$SCOPED"
require "the grant this check made is gone again" \
  bash -c '! kubectl get clusterrolebinding verify-act9-view >/dev/null 2>&1'
answer_check "${ANSWER:-}"
verdict
