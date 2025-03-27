import './pico.min.css'
import $ from 'jquery'



let counter = 1
export function doSomething() {
    counter += 1
    console.log('pico ' + counter)
    console.log($('#item'))
}
window.doSomething = doSomething()



